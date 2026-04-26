"use client"

import { useState, useRef, useEffect } from "react"
import {
  Camera,
  ImageIcon,
  Leaf,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Clock,
  Settings,
  X,
  Trash2,
  Loader2,
  AlertCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import {
  blobToBase64,
  compressImage,
  createImagePreview,
  createThumbnailDataUrl,
  revokeImagePreview,
} from "@/lib/image-compression"
import { analyzeImage, type AnalyzeResponse } from "@/lib/api"

type Page = "scan" | "compressing" | "uploading" | "processing" | "results" | "history" | "settings"
type ProcessingStage = "compressing" | "uploading" | "analyzing"

interface Ingredient {
  name: string
  code?: string
  description: string
  impact: "positive" | "neutral" | "negative"
}

interface ScanHistory {
  id: string
  date: Date
  productName: string
  grade: string
  score: number
  thumbnail: string
  analysisData: AnalyzeResponse
}

const HISTORY_STORAGE_KEY = "scanHistory"
const HISTORY_LIMIT = 20
const PLACEHOLDER_IMAGE = "/placeholder.svg"

const COMMON_ALLERGENS = [
  "Peanuts",
  "Tree Nuts (Almonds, Cashews, etc.)",
  "Milk/Dairy",
  "Eggs",
  "Soy",
  "Wheat/Gluten",
  "Fish",
  "Shellfish",
  "Sesame",
  "Mustard",
  "Celery",
  "Sulfites",
]

export default function IngrediScanAI() {
  const [currentPage, setCurrentPage] = useState<Page>("scan")
  const [progress, setProgress] = useState(0)
  const [processingStage, setProcessingStage] = useState<ProcessingStage>("compressing")
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [selectedAllergens, setSelectedAllergens] = useState<string[]>([])
  const [currentImage, setCurrentImage] = useState<string | null>(null)
  const [currentImageFile, setCurrentImageFile] = useState<File | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [scanHistory, setScanHistory] = useState<ScanHistory[]>([])
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  // 历史记录只保存在当前浏览器本地；后端不保存图片或分析结果。
  useEffect(() => {
    const savedHistory = localStorage.getItem(HISTORY_STORAGE_KEY)
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory)
        const loaded = parsed.slice(0, HISTORY_LIMIT).map((item: any) => {
          const thumbnail =
            typeof item.thumbnail === "string" && item.thumbnail.startsWith("data:")
              ? item.thumbnail
              : PLACEHOLDER_IMAGE

          return {
            id: String(item.id || Date.now()),
            date: new Date(item.date),
            productName: item.productName || item.summary || "Unknown Product",
            grade: item.grade || item.analysisData?.health_score || "",
            score: Number(item.score || parseScoreFromSummary(item.summary || item.analysisData?.summary || "")),
            thumbnail,
            analysisData: item.analysisData || {
              health_score: item.grade || "",
              summary: item.productName || "",
              risks: [],
              full_ingredients: [],
              alternatives: [],
            },
          }
        })
        setScanHistory(loaded)
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(loaded))
      } catch (e) {
        console.error('加载历史记录失败:', e)
        localStorage.removeItem(HISTORY_STORAGE_KEY)
      }
    }
  }, [])

  const persistHistory = (items: ScanHistory[]) => {
    const limited = items.slice(0, HISTORY_LIMIT).map((item) => ({
      id: item.id,
      date: item.date,
      productName: item.productName,
      grade: item.grade,
      score: item.score,
      thumbnail: item.thumbnail,
      analysisData: item.analysisData,
    }))

    try {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(limited))
      setScanHistory(limited)
    } catch (e: any) {
      console.warn("历史记录存储空间不足，缩减保存数量", e)
      const trimmed = limited.slice(0, Math.min(8, HISTORY_LIMIT)).map((item) => ({
        ...item,
        thumbnail: PLACEHOLDER_IMAGE,
      }))
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(trimmed))
      setScanHistory(trimmed)
    }
  }

  const saveToHistory = (result: AnalyzeResponse, thumbnail: string) => {
    const newItem: ScanHistory = {
      id: Date.now().toString(),
      date: new Date(),
      productName: result.summary || "Unknown Product",
      grade: result.health_score,
      score: parseScoreFromSummary(result.summary),
      thumbnail,
      analysisData: result,
    }
    persistHistory([newItem, ...scanHistory])
  }
  
  const loadHistoryItem = (item: ScanHistory) => {
    if (!item.analysisData) {
      setError('历史记录数据不完整，无法查看详情')
      setCurrentPage("scan")
      return
    }
    
    setError(null)
    setProgress(100)
    setIsDetailsOpen(false)
    setAnalysisResult(item.analysisData)
    setCurrentImage(item.thumbnail || PLACEHOLDER_IMAGE)
    setCurrentPage("results")
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const parseScoreFromSummary = (summary: string): number => {
    const match = summary.match(/(\d+)%/)
    return match ? parseInt(match[1]) : 50
  }

  const handleFileSelect = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('请选择图片文件')
      return
    }

    setError(null)
    setCurrentImageFile(file)
    setCurrentPage("compressing")
    setProgress(0)
    setProcessingStage("compressing")

    try {
      // 创建预览
      const previewUrl = createImagePreview(file)
      setCurrentImage(previewUrl)

      // 压缩图片
      setProgress(20)
      const compressedBlob = await compressImage(file, {
        maxWidthOrHeight: 512,
        quality: 0.65,
        maxSizeMB: 0.45,
      })
      const historyThumbnail = await createThumbnailDataUrl(compressedBlob)

      setProgress(40)
      setProcessingStage("uploading")

      // 转换为 Base64
      const base64 = await blobToBase64(compressedBlob)
      const imageType = file.type || 'image/jpeg'

      setProgress(60)
      setProcessingStage("analyzing")
      setCurrentPage("processing")

      // 调用分析 API
      const result = await analyzeImage(base64, imageType)
      
      setAnalysisResult(result)
      setProgress(100)
      
      // 历史记录只保存小缩略图，避免浏览器本地存储被大图占满。
      if (!result.error) {
        saveToHistory(result, historyThumbnail)
      }
      
      setTimeout(() => {
        setCurrentPage("results")
      }, 500)
    } catch (err) {
      console.error('处理失败:', err)
      // 创建错误响应对象
      const errorMessage = err instanceof Error ? err.message : '处理失败，请重试'
      const loweredErrorMessage = errorMessage.toLowerCase()
      let errorType: 'invalid_image' | 'api_error' | 'parse_error' | 'server_error' | 'unknown_error' = 'unknown_error'
      let userMessage = errorMessage
      
      // 根据错误信息判断错误类型
      if (
        errorMessage.includes('网络') ||
        errorMessage.includes('连接') ||
        loweredErrorMessage.includes('network') ||
        loweredErrorMessage.includes('fetch') ||
        loweredErrorMessage.includes('load failed') ||
        loweredErrorMessage.includes('failed to fetch') ||
        loweredErrorMessage.includes('cors')
      ) {
        errorType = 'api_error'
        userMessage = '网络连接失败（可能是跨域配置或后端地址问题），请稍后重试'
      } else if (errorMessage.includes('超时') || loweredErrorMessage.includes('timeout')) {
        errorType = 'api_error'
        userMessage = '请求超时，请稍后重试'
      } else if (errorMessage.includes('图片') || errorMessage.includes('image')) {
        errorType = 'invalid_image'
        userMessage = '图片格式错误或无法解析，请上传清晰的商品标签图片'
      } else if (errorMessage.includes('解析') || errorMessage.includes('parse')) {
        errorType = 'parse_error'
        userMessage = '数据解析失败，请重新上传图片'
      }
      
      const errorResult: AnalyzeResponse = {
        health_score: "",
        summary: "",
        risks: [],
        full_ingredients: [],
        alternatives: [],
        error: userMessage,
        error_type: errorType
      }
      setAnalysisResult(errorResult)
      setProgress(100)
      setTimeout(() => {
        setCurrentPage("results")
      }, 500)
    }
  }

  const handleCameraClick = () => {
    if (cameraInputRef.current) {
      cameraInputRef.current.click()
    }
  }

  const handleAlbumClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
    // 重置 input 以便可以再次选择同一文件
    e.target.value = ''
  }

  const handleCameraInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
    // 重置 input
    e.target.value = ''
  }

  const toggleAllergen = (allergen: string) => {
    setSelectedAllergens((prev) => (prev.includes(allergen) ? prev.filter((a) => a !== allergen) : [...prev, allergen]))
  }

  const deleteHistoryItem = (id: string) => {
    const updated = scanHistory.filter((item) => item.id !== id)
    persistHistory(updated)
  }

  // 将分析结果转换为 Ingredient 格式
  const convertToIngredients = (result: AnalyzeResponse): Ingredient[] => {
    const ingredients: Ingredient[] = []

    result.risks.forEach((risk) => {
      const impact = risk.level === 'High' ? 'negative' : risk.level === 'Moderate' ? 'neutral' : 'positive'
      const codeMatch = risk.name.match(/\(([A-Z]\d+)\)/)
      ingredients.push({
        name: risk.name.replace(/\s*\([A-Z]\d+\)\s*/, ''),
        code: codeMatch ? codeMatch[1] : undefined,
        description: risk.desc,
        impact,
      })
    })

    // 添加其他成分（不在风险列表中的）
    result.full_ingredients.forEach((name) => {
      if (!ingredients.some((ing) => ing.name === name)) {
        ingredients.push({
          name,
          description: '成分信息',
          impact: 'positive',
        })
      }
    })

    return ingredients
  }

  const getHealthScore = (result: AnalyzeResponse) => {
    const scoreMatch = result.summary.match(/(\d+)%/)
    const percentage = scoreMatch ? parseFloat(scoreMatch[1]) : 50

    if (percentage >= 70)
      return { grade: result.health_score || "A", color: "text-primary", bg: "bg-primary", label: "Good", score: percentage }
    if (percentage >= 50)
      return { grade: result.health_score || "B", color: "text-yellow-600", bg: "bg-yellow-500", label: "Fair", score: percentage }
    return { grade: result.health_score || "C", color: "text-destructive", bg: "bg-destructive", label: "Poor", score: percentage }
  }

  const ingredients = analysisResult ? convertToIngredients(analysisResult) : []
  const highRiskIngredients = ingredients.filter((i) => i.impact === "negative")
  const moderateRiskIngredients = ingredients.filter((i) => i.impact === "neutral")
  const health = analysisResult ? getHealthScore(analysisResult) : { grade: "B", color: "text-yellow-600", bg: "bg-yellow-500", label: "Fair", score: 50 }

  const handleReset = () => {
    if (currentImage?.startsWith("blob:")) {
      revokeImagePreview(currentImage)
    }
    setCurrentImage(null)
    setCurrentImageFile(null)
    setAnalysisResult(null)
    setError(null)
    setProgress(0)
    setCurrentPage("scan")
  }

  return (
    <div className="flex flex-col min-h-screen bg-background safe-area-inset">
      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileInputChange}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleCameraInputChange}
      />

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Page 1: Scan Homepage */}
        {currentPage === "scan" && (
          <div className="flex flex-col items-center justify-center min-h-screen px-6 relative safe-area-inset">
            {error && (
              <div className="absolute top-20 left-6 right-6 z-50">
                <Card className="border-destructive bg-destructive/10">
                  <CardContent className="p-4 flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-destructive">{error}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setError(null)}
                      className="h-8 w-8 p-0"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}

            <div className="absolute top-6 right-6 flex items-center gap-3 z-10">
              <button
                onClick={() => setCurrentPage("history")}
                className="w-10 h-10 rounded-full bg-foreground/10 backdrop-blur-sm hover:bg-foreground/20 transition-colors flex items-center justify-center"
                aria-label="View History"
              >
                <Clock className="w-5 h-5 text-foreground/80" />
              </button>
              <button
                onClick={() => setCurrentPage("settings")}
                className="w-10 h-10 rounded-full bg-foreground/10 backdrop-blur-sm hover:bg-foreground/20 transition-colors flex items-center justify-center"
                aria-label="Settings"
              >
                <Settings className="w-5 h-5 text-foreground/80" />
              </button>
            </div>

            <div className="text-center mb-8 space-y-3">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Leaf className="w-8 h-8 text-primary" />
                <h1 className="text-3xl font-bold text-balance">IngrediScan AI</h1>
              </div>
              <p className="text-muted-foreground text-balance max-w-md leading-relaxed">
                扫描产品包装以分析成分并识别潜在健康风险
              </p>
            </div>

            <div className="relative mb-8">
              <button
                onClick={handleCameraClick}
                className="relative w-48 h-48 rounded-full bg-primary hover:bg-primary/90 transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center justify-center group"
              >
                <Camera className="w-16 h-16 text-primary-foreground" />
                <div className="absolute inset-0 rounded-full border-4 border-primary/20 group-hover:border-primary/40 transition-colors" />
              </button>
              <p className="text-center mt-4 font-medium">拍照</p>
            </div>

            <button
              onClick={handleAlbumClick}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ImageIcon className="w-5 h-5" />
              <span className="text-sm">从相册选择</span>
            </button>
          </div>
        )}

        {/* Page 2: Processing (Compressing/Uploading/Analyzing) */}
        {(currentPage === "compressing" || currentPage === "processing") && (
          <div className="flex flex-col items-center justify-center min-h-screen px-6">
            <div className="w-full max-w-md space-y-8">
              {currentImage && (
                <div className="relative aspect-square rounded-2xl overflow-hidden bg-muted">
                  <img
                    src={currentImage}
                    alt="正在分析的产品"
                    className="w-full h-full object-cover"
                  />
                  {/* AI Scan Line Animation */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-full h-1 bg-primary shadow-[0_0_20px_rgba(34,197,94,0.8)] animate-pulse" />
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <Progress value={progress} className="h-2" />
                <div className="text-center space-y-2">
                  <div className="flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 text-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">
                      {processingStage === "compressing" && "正在压缩图片..."}
                      {processingStage === "uploading" && "正在上传..."}
                      {processingStage === "analyzing" && "AI 正在分析成分和健康风险..."}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">{progress}% 完成</p>
                </div>
              </div>

              {error && (
                <Card className="border-destructive bg-destructive/10">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
                      <p className="text-sm text-destructive">{error}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full mt-4"
                      onClick={handleReset}
                    >
                      返回重试
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* Page 3: Results */}
        {currentPage === "results" && analysisResult && (
          <div className="min-h-screen flex flex-col px-6 py-8 space-y-6 safe-area-inset">
            {/* 显示历史记录标识（如果是从历史记录加载的） */}
            {currentImage && !currentImage.startsWith('blob:') && currentImage !== PLACEHOLDER_IMAGE && (
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground bg-muted/50 px-4 py-2 rounded-lg">
                <Clock className="w-4 h-4" />
                <span>查看历史记录</span>
              </div>
            )}
            
            {/* 错误提示页面 */}
            {analysisResult.error ? (
              <>
                <Card className="border-destructive bg-destructive/10">
                  <CardContent className="p-8 text-center space-y-4">
                    <div className="flex justify-center">
                      <AlertCircle className="w-16 h-16 text-destructive" />
                    </div>
                    <h2 className="text-2xl font-bold text-destructive">分析失败</h2>
                    <p className="text-muted-foreground text-lg">{analysisResult.error}</p>
                    
                    {analysisResult.error_type === "invalid_image" && (
                      <div className="mt-4 p-4 bg-background rounded-lg border border-border">
                        <p className="text-sm font-medium mb-3">请上传商品标签图片，包含以下内容：</p>
                        <ul className="text-sm text-muted-foreground space-y-2 text-left">
                          <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            <span>商品包装的完整标签（食品、化妆品、药品等）</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            <span>清晰的成分列表或配料表信息</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            <span>避免上传风景、人物、动物等非商品标签图片</span>
                          </li>
                        </ul>
                      </div>
                    )}
                    
                    {analysisResult.error_type === "api_error" && (
                      <div className="mt-4 p-4 bg-background rounded-lg border border-border">
                        <p className="text-sm font-medium mb-2">可能的原因：</p>
                        <ul className="text-sm text-muted-foreground space-y-1 text-left list-disc list-inside">
                          <li>网络连接不稳定</li>
                          <li>API 服务暂时繁忙</li>
                          <li>请检查网络连接后重试</li>
                        </ul>
                      </div>
                    )}
                    
                    {analysisResult.error_type === "parse_error" && (
                      <div className="mt-4 p-4 bg-background rounded-lg border border-border">
                        <p className="text-sm font-medium mb-2">建议：</p>
                        <ul className="text-sm text-muted-foreground space-y-1 text-left list-disc list-inside">
                          <li>确保图片清晰，文字可读</li>
                          <li>确保上传的是商品标签图片</li>
                          <li>尝试重新拍摄或选择图片</li>
                        </ul>
                      </div>
                    )}
                    
                    {analysisResult.error_type === "server_error" && (
                      <div className="mt-4 p-4 bg-background rounded-lg border border-border">
                        <p className="text-sm text-muted-foreground">
                          服务器处理出错，请稍后重试。如问题持续，请联系技术支持。
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
                
                <Button size="lg" className="w-full h-12 text-base" onClick={handleReset}>
                  <Camera className="w-5 h-5 mr-2" />
                  重新扫描
                </Button>
              </>
            ) : (
              <>
                {analysisResult.confidence && analysisResult.confidence < 0.7 && (
                  <Card className="border-yellow-500/50 bg-yellow-500/5">
                    <CardContent className="p-4 flex items-center gap-3">
                      <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
                      <p className="text-sm text-yellow-600">
                        注意：由于图片质量较低，分析结果置信度较低，仅供参考
                      </p>
                    </CardContent>
                  </Card>
                )}

                <div className={cn("rounded-2xl p-8 text-center space-y-3", health.bg)}>
              <div className="text-white/90 text-sm font-medium uppercase tracking-wide">健康评分</div>
              <div className="text-white text-7xl font-bold">{health.grade}</div>
              <div className="text-white/90 text-lg font-medium">{health.label}</div>
              <div className="text-white/80 text-sm">{Math.round(health.score)}% 健康</div>
            </div>

            <div className="space-y-4">
              <h2 className="text-xl font-bold">成分警告</h2>

              {/* High Risk Warnings */}
              {highRiskIngredients.length > 0 && (
                <Card className="border-destructive/50 bg-destructive/5">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-destructive" />
                      <CardTitle className="text-base text-destructive">高风险成分</CardTitle>
                    </div>
                    <CardDescription>建议避免或限制摄入</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {highRiskIngredients.map((ingredient, idx) => (
                      <div key={`${ingredient.name}-${idx}`} className="p-3 rounded-lg bg-background border border-destructive/30">
                        <div className="flex items-start gap-2 mb-2">
                          <div className="w-2 h-2 rounded-full bg-destructive mt-1.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-sm">
                              {ingredient.name}{" "}
                              {ingredient.code && <span className="text-muted-foreground">({ingredient.code})</span>}
                            </h3>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed text-balance ml-4">
                          {ingredient.description}
                        </p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Moderate Risk Warnings */}
              {moderateRiskIngredients.length > 0 && (
                <Card className="border-yellow-500/50 bg-yellow-500/5">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-yellow-600" />
                      <CardTitle className="text-base text-yellow-600">中等风险成分</CardTitle>
                    </div>
                    <CardDescription>适量食用</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {moderateRiskIngredients.map((ingredient, idx) => (
                      <div key={`${ingredient.name}-${idx}`} className="p-3 rounded-lg bg-background border border-yellow-500/30">
                        <div className="flex items-start gap-2 mb-2">
                          <div className="w-2 h-2 rounded-full bg-yellow-600 mt-1.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-sm">
                              {ingredient.name}{" "}
                              {ingredient.code && <span className="text-muted-foreground">({ingredient.code})</span>}
                            </h3>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed text-balance ml-4">
                          {ingredient.description}
                        </p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Alternatives */}
            {analysisResult.alternatives && analysisResult.alternatives.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Leaf className="w-5 h-5 text-primary" />
                    更健康的替代品
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {analysisResult.alternatives.map((alt, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                        <span className="text-sm">{alt}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            <Collapsible open={isDetailsOpen} onOpenChange={setIsDetailsOpen} className="space-y-2">
              <CollapsibleTrigger asChild>
                <Button variant="outline" size="lg" className="w-full h-12 text-base bg-transparent">
                  {isDetailsOpen ? (
                    <>
                      <ChevronUp className="w-5 h-5 mr-2" />
                      隐藏成分详情
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-5 h-5 mr-2" />
                      查看完整成分列表
                    </>
                  )}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Leaf className="w-5 h-5 text-primary" />
                      完整成分列表
                    </CardTitle>
                    <CardDescription>此产品中发现的所有成分</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {analysisResult.full_ingredients.map((name, idx) => {
                      const ingredient = ingredients.find((ing) => ing.name === name)
                      // 优先使用 ingredients_detail 中的描述
                      const detail = analysisResult.ingredients_detail?.find((d) => d.name === name)
                      const description = detail?.description || ingredient?.description
                      
                      return (
                        <div key={`${name}-${idx}`} className="p-3 rounded-lg border border-border space-y-2">
                          <div className="flex items-center gap-3">
                            <div
                              className={cn(
                                "w-2 h-2 rounded-full flex-shrink-0",
                                ingredient?.impact === "positive" && "bg-primary",
                                ingredient?.impact === "neutral" && "bg-muted-foreground",
                                ingredient?.impact === "negative" && "bg-destructive",
                                !ingredient && "bg-muted-foreground",
                              )}
                            />
                            <span className="font-medium text-sm">
                              {name}{" "}
                              {ingredient?.code && (
                                <span className="text-muted-foreground text-xs">({ingredient.code})</span>
                              )}
                            </span>
                          </div>
                          {description && (
                            <p className="text-sm text-muted-foreground leading-relaxed text-balance ml-5">
                              {description}
                            </p>
                          )}
                        </div>
                      )
                    })}
                  </CardContent>
                </Card>
              </CollapsibleContent>
            </Collapsible>

            {/* Rescan Button */}
            <Button size="lg" className="w-full h-12 text-base" onClick={handleReset}>
              <Camera className="w-5 h-5 mr-2" />
              扫描另一个产品
            </Button>

                {/* Legal Disclaimer */}
                <div className="pt-4 border-t border-border">
                  <p className="text-xs text-muted-foreground text-center leading-relaxed text-balance">
                    此分析仅供参考，不应替代专业医疗建议。请咨询医疗保健提供者以获得个性化建议。
                  </p>
                </div>
              </>
            )}
          </div>
        )}

        {currentPage === "history" && (
          <div className="min-h-screen flex flex-col px-6 py-8 safe-area-inset">
            {/* Header with back button */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Clock className="w-6 h-6 text-primary" />
                <h1 className="text-2xl font-bold">扫描历史</h1>
              </div>
              <button
                onClick={() => setCurrentPage("scan")}
                className="w-9 h-9 rounded-full hover:bg-muted transition-colors flex items-center justify-center"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {scanHistory.length === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center space-y-3">
                  <Clock className="w-16 h-16 text-muted-foreground/50 mx-auto" />
                  <p className="text-muted-foreground">暂无扫描历史</p>
                  <Button onClick={() => setCurrentPage("scan")}>
                    <Camera className="w-4 h-4 mr-2" />
                    开始扫描
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {scanHistory.map((item) => (
                  <Card 
                    key={item.id} 
                    className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer active:scale-[0.98]"
                    onClick={() => loadHistoryItem(item)}
                  >
                    <div className="flex gap-4 p-4">
                      {/* Thumbnail */}
                      <div className="w-20 h-20 rounded-lg overflow-hidden bg-muted flex-shrink-0">
                        <img
                          src={item.thumbnail || PLACEHOLDER_IMAGE}
                          alt={item.productName}
                          className="w-full h-full object-cover"
                        />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-start justify-between gap-2">
                          <h3 className="font-semibold text-sm line-clamp-2 flex-1">{item.productName}</h3>
                          <button
                            onClick={(e) => {
                              e.stopPropagation() // 阻止触发卡片点击
                              deleteHistoryItem(item.id)
                            }}
                            className="flex-shrink-0 w-8 h-8 rounded-full hover:bg-destructive/10 transition-colors flex items-center justify-center"
                            aria-label="Delete"
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </button>
                        </div>

                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              "px-2.5 py-1 rounded-md text-xs font-bold text-white",
                              item.grade === "A" && "bg-primary",
                              item.grade === "B" && "bg-yellow-500",
                              item.grade === "C" && "bg-destructive",
                              item.grade === "D" && "bg-orange-500",
                              item.grade === "E" && "bg-red-600",
                            )}
                          >
                            等级 {item.grade}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {item.date.toLocaleDateString("zh-CN", { month: "short", day: "numeric", year: "numeric" })}
                          </span>
                        </div>
                        
                        {/* 点击提示 */}
                        <p className="text-xs text-muted-foreground mt-1">点击查看详情</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {currentPage === "settings" && (
          <div className="min-h-screen flex flex-col px-6 py-8 safe-area-inset">
            {/* Header with back button */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Settings className="w-6 h-6 text-primary" />
                <h1 className="text-2xl font-bold">过敏原设置</h1>
              </div>
              <button
                onClick={() => setCurrentPage("scan")}
                className="w-9 h-9 rounded-full hover:bg-muted transition-colors flex items-center justify-center"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>选择您的过敏原</CardTitle>
                <CardDescription>当产品含有这些成分时，我们会提醒您</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {COMMON_ALLERGENS.map((allergen) => (
                  <div
                    key={allergen}
                    className="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <Checkbox
                      id={allergen}
                      checked={selectedAllergens.includes(allergen)}
                      onCheckedChange={() => toggleAllergen(allergen)}
                    />
                    <label
                      htmlFor={allergen}
                      className="flex-1 text-sm font-medium leading-none cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {allergen}
                    </label>
                  </div>
                ))}
              </CardContent>
            </Card>

            {selectedAllergens.length > 0 && (
              <div className="mt-6 p-4 rounded-lg bg-primary/5 border border-primary/20">
                <p className="text-sm text-foreground/80">
                  已选择 <strong className="text-primary">{selectedAllergens.length}</strong> 个过敏原
                </p>
              </div>
            )}

            <Button size="lg" className="w-full h-12 text-base mt-6" onClick={() => setCurrentPage("scan")}>
              保存设置
            </Button>
          </div>
        )}
      </main>
    </div>
  )
}
