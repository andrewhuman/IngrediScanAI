import imageCompression from 'browser-image-compression'

export interface CompressionOptions {
  maxSizeMB?: number
  maxWidthOrHeight?: number
  useWebWorker?: boolean
  quality?: number
}

/**
 * 压缩图片以适配 OCR 和 VLM 模型
 * @param file 原始图片文件
 * @param options 压缩选项
 * @returns 压缩后的 Blob
 */
export async function compressImage(
  file: File,
  options: CompressionOptions = {}
): Promise<Blob> {
  const {
    maxSizeMB = 1,
    maxWidthOrHeight = 1024,
    useWebWorker = true,
    quality = 0.8,
  } = options

  try {
    const compressedFile = await imageCompression(file, {
      maxSizeMB,
      maxWidthOrHeight,
      useWebWorker,
      quality,
    })

    return compressedFile
  } catch (error) {
    console.error('图片压缩失败:', error)
    throw new Error('图片压缩失败，请重试')
  }
}

/**
 * 将 Blob 转换为 Base64 字符串
 */
export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
      } else {
        reject(new Error('转换失败'))
      }
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

/**
 * 创建图片预览 URL
 */
export function createImagePreview(file: File | Blob): string {
  return URL.createObjectURL(file)
}

/**
 * 释放预览 URL 以释放内存
 */
export function revokeImagePreview(url: string): void {
  URL.revokeObjectURL(url)
}
