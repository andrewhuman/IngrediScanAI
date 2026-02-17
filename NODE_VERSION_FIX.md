# Node.js 版本问题修复指南

## 问题
当前 Node.js 版本：v12.22.9  
Next.js 16 要求：Node.js >= 20.9.0

## 解决方案

### 方案 1：使用 NodeSource 仓库安装 Node.js 20（推荐，适用于 Debian/Ubuntu）

```bash
# 1. 安装 NodeSource 仓库
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# 2. 安装 Node.js 20
sudo apt-get install -y nodejs

# 3. 验证版本
node --version  # 应该显示 v20.x.x
npm --version

# 4. 重新安装依赖并构建
cd /home/xyd_hc/下载/IngrediScanAI
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 方案 2：使用 nvm（如果方案 1 失败）

1. **手动下载并安装 nvm**：
```bash
# 如果 curl 失败，可以手动下载
wget https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh
bash install.sh
```

2. **重新加载 shell**：
```bash
source ~/.bashrc
```

3. **安装 Node.js 20**：
```bash
nvm install 20
nvm use 20
nvm alias default 20
```

### 方案 3：从官网下载二进制文件

1. 访问：https://nodejs.org/dist/v20.18.0/
2. 下载 Linux x64 版本：`node-v20.18.0-linux-x64.tar.xz`
3. 解压并设置 PATH：
```bash
tar -xf node-v20.18.0-linux-x64.tar.xz
sudo mv node-v20.18.0-linux-x64 /opt/nodejs
echo 'export PATH=/opt/nodejs/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 方案 4：临时降级 Next.js（不推荐，仅用于测试）

如果暂时无法升级 Node.js，可以降级到兼容版本：

```bash
npm install next@13.5.6 react@18.2.0 react-dom@18.2.0
npm install --save-dev @types/react@18 @types/react-dom@18
```

**注意**：降级会失去 Next.js 16 的新特性，建议尽快升级 Node.js。

## 验证

升级 Node.js 后，运行：
```bash
node --version  # 应该 >= 20.9.0
npm run build   # 应该成功
```

## 如果仍有问题

如果所有方案都失败，请检查：
1. 网络连接是否正常
2. 是否有足够的磁盘空间
3. 是否有 sudo 权限（方案 1 需要）
