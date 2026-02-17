# ⚠️ 必须升级 Node.js

## 当前状态
- **当前 Node.js 版本**: v12.22.9
- **最低要求**: Node.js 16.14.0+ (Next.js 13) 或 20.9.0+ (Next.js 16)
- **问题**: Node.js 12 不支持可选链操作符 (`?.`) 等现代 JavaScript 特性

## 🚀 快速升级方案

### 方案 1：使用 NodeSource 仓库（推荐，最简单）

**在终端中执行以下命令（需要 sudo 权限）：**

```bash
# 1. 添加 NodeSource 仓库
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# 2. 安装 Node.js 20 LTS
sudo apt-get install -y nodejs

# 3. 验证安装
node --version  # 应该显示 v20.x.x
npm --version

# 4. 重新安装项目依赖
cd /home/xyd_hc/下载/IngrediScanAI
rm -rf node_modules package-lock.json
npm install

# 5. 恢复 Next.js 16（可选，但推荐）
npm install next@16.0.10 react@19.2.0 react-dom@19.2.0
npm install --save-dev @types/react@^19 @types/react-dom@^19

# 6. 构建项目
npm run build
```

### 方案 2：手动下载安装（如果方案 1 失败）

1. **下载 Node.js 20 LTS**：
   ```bash
   cd /tmp
   wget https://nodejs.org/dist/v20.18.0/node-v20.18.0-linux-x64.tar.xz
   tar -xf node-v20.18.0-linux-x64.tar.xz
   ```

2. **安装到系统目录**：
   ```bash
   sudo mv node-v20.18.0-linux-x64 /opt/nodejs
   sudo ln -sf /opt/nodejs/bin/node /usr/local/bin/node
   sudo ln -sf /opt/nodejs/bin/npm /usr/local/bin/npm
   ```

3. **验证**：
   ```bash
   node --version  # 应该显示 v20.18.0
   ```

### 方案 3：使用 nvm（无需 sudo）

如果无法使用 sudo，可以安装 nvm 到用户目录：

```bash
# 1. 下载 nvm 安装脚本
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 2. 重新加载 shell 配置
source ~/.bashrc

# 3. 安装 Node.js 20
nvm install 20
nvm use 20
nvm alias default 20

# 4. 验证
node --version
```

**注意**：使用 nvm 时，每次新开终端都需要运行 `nvm use 20`，或设置 `nvm alias default 20`。

## 📝 升级后的步骤

1. **恢复 package.json**（如果降级了 Next.js）：
   ```bash
   git checkout package.json  # 如果有 git
   # 或手动恢复 Next.js 16 版本
   ```

2. **重新安装依赖**：
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **构建项目**：
   ```bash
   npm run build
   ```

4. **启动开发服务器**：
   ```bash
   npm run dev
   ```

## ❓ 常见问题

### Q: 为什么必须升级？
A: Next.js 13+ 使用了 ES2020 特性（如可选链 `?.`），Node.js 12 不支持这些特性。

### Q: 升级会影响其他项目吗？
A: 如果使用 nvm，不会影响。如果系统级安装，可能会影响，但 Node.js 20 向后兼容。

### Q: 升级后项目还能运行吗？
A: 是的，升级 Node.js 后项目应该能正常运行，甚至性能更好。

## ✅ 验证清单

升级完成后，确认：
- [ ] `node --version` 显示 v20.x.x
- [ ] `npm --version` 正常工作
- [ ] `npm install` 成功
- [ ] `npm run build` 成功
- [ ] `npm run dev` 可以启动开发服务器
