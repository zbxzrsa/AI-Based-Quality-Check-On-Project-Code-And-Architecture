# GitHub OAuth 配置指南

## 当前问题
连接 GitHub 时显示错误：`Configuration Error: GitHub Client ID is not configured. Please contact administrator.`

## 解决方案

### 1. 验证 GitHub OAuth App 配置

当前配置的 Client ID: `your_github_client_id`

请在 GitHub 上验证此 OAuth App：

1. 访问 [GitHub Developer Settings](https://github.com/settings/developers)
2. 点击 "OAuth Apps"
3. 找到对应的应用（Client ID: `your_github_client_id`）
4. 确认以下配置：
   - **Application name**: 你的应用名称
   - **Homepage URL**: `http://localhost:3000` (开发环境)
   - **Authorization callback URL**: `http://localhost:3000/api/github/callback`

### 2. 如果 OAuth App 不存在或需要重新创建

#### 创建新的 GitHub OAuth App：

1. 访问 https://github.com/settings/developers
2. 点击 "New OAuth App"
3. 填写以下信息：
   - **Application name**: AI Code Review Platform (或你的应用名称)
   - **Homepage URL**: `http://localhost:3000`
   - **Application description**: (可选)
   - **Authorization callback URL**: `http://localhost:3000/api/github/callback`
4. 点击 "Register application"
5. 记录 **Client ID** 和生成 **Client Secret**

#### 更新环境配置：

编辑 `frontend/.env.local` 文件：

```env
NEXT_PUBLIC_GITHUB_CLIENT_ID=你的新Client_ID
GITHUB_CLIENT_SECRET=你的Client_Secret
```

### 3. 重启开发服务器

配置更新后，需要重启前端服务器：

```bash
cd frontend
npm run dev
```

### 4. 生产环境配置

对于生产环境，需要：

1. 创建单独的 GitHub OAuth App
2. 设置正确的生产环境 URL：
   - **Homepage URL**: `https://你的域名.com`
   - **Authorization callback URL**: `https://你的域名.com/api/github/callback`
3. 在生产环境变量中配置相应的 Client ID 和 Secret

## 已完成的修改

✅ 已删除 Dashboard 页面的 "Add Project" 按钮
- 文件：`frontend/src/app/dashboard/page.tsx`
- 移除了页面头部的 "Add Project" 按钮及其图标导入

## 测试步骤

1. 确保 GitHub OAuth App 配置正确
2. 重启前端开发服务器
3. 访问 Dashboard 页面，确认 "Add Project" 按钮已被移除
4. 尝试连接 GitHub（如果还有其他地方有此功能）

## 注意事项

- Client Secret 不应该提交到版本控制系统
- 确保 `.env.local` 文件在 `.gitignore` 中
- 开发和生产环境应使用不同的 OAuth App
