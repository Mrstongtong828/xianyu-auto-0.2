# Windows Docker 安装器用户指南

本文面向不熟悉命令行、希望在 Windows 上通过安装器或启动器运行咸鱼自动回复后台的用户。

## 前置条件

- Windows 10/11。
- 已安装 Docker Desktop，并确保 Docker Desktop 已启动且状态为 Running。
- 本机 `127.0.0.1:8000` 端口未被占用。
- 首次安装时准备一个管理员密码，不要使用弱密码。

不需要用户手动安装 Python、Playwright、Chromium 或项目依赖；这些运行环境由 Docker 镜像提供。

## 首次安装

推荐使用安装器入口：

```powershell
.\installer\install.cmd
```

如果只是想预览会执行哪些操作，不改写 `.env`、不启动容器：

```powershell
.\installer\install.cmd -DryRun
```

安装器会执行以下动作：

- 检查 Docker CLI 和 Docker Compose。
- 在 Docker Desktop 已安装但未启动时尝试启动 Docker Desktop。
- 创建 `data/`、`logs/`、`backups/`、`static/uploads/images/`。
- 创建或补齐 `.env`，保留已有非空配置。
- 首次缺少 `ADMIN_PASSWORD` 时提示输入管理员密码。
- 自动生成 `JWT_SECRET_KEY` 和 `SECRET_ENCRYPTION_KEY`。
- 使用 `docker-compose-cn.yml` 启动服务。
- 等待 `http://127.0.0.1:8000/health` 可用。
- 成功后打开 `http://127.0.0.1:8000`。

## 常用命令

启动服务：

```powershell
.\installer\start.cmd
```

停止服务，不删除数据：

```powershell
.\installer\stop.cmd
```

查看状态：

```powershell
.\installer\status.cmd
```

查看日志：

```powershell
.\installer\logs.cmd -Tail 120
```

打开后台：

```powershell
.\installer\open.cmd
```

卸载容器和网络，但保留数据：

```powershell
.\installer\uninstall.cmd
```

删除本地数据需要显式传入 `-RemoveData`，并按提示确认：

```powershell
.\installer\uninstall.cmd -RemoveData
```

## 数据保存位置

运行数据保存在项目目录下：

- `data/`：数据库和业务数据。
- `logs/`：运行日志。
- `backups/`：备份文件。
- `static/uploads/`：上传文件。
- `.env`：管理员密码、JWT 密钥、邮件配置等敏感配置。

默认卸载不会删除这些文件。迁移或重装前，请备份这些目录和 `.env`。

## 管理员密码

首次安装器会在 `.env` 缺少 `ADMIN_PASSWORD` 时提示输入密码。也可以手动编辑 `.env`：

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD=你的强密码
```

修改后重启服务：

```powershell
.\installer\stop.cmd
.\installer\start.cmd
```

## 端口和安全默认值

当前安装器默认使用 `docker-compose-cn.yml`，后台地址是：

```text
http://127.0.0.1:8000
```

端口绑定在 `127.0.0.1`，只允许本机访问。这是有意的安全默认值，避免后台直接暴露到局域网或公网。

如果需要换端口，修改 `docker-compose-cn.yml`：

```yaml
ports:
  - "127.0.0.1:8010:8090"
```

然后访问：

```text
http://127.0.0.1:8010
```

## 常见问题

### Docker Desktop 未运行

现象：提示 Docker engine 未就绪，或 `docker info` 失败。

处理：

1. 打开 Docker Desktop。
2. 等待状态变为 Running。
3. 重新运行 `.\installer\start.cmd`。
4. 如果仍失败，重启 Docker Desktop 或 Windows。

### 端口被占用

现象：容器启动失败，日志里出现端口绑定失败。

处理：

1. 检查是否已有程序占用 `8000`。
2. 修改 `docker-compose-cn.yml` 的左侧端口。
3. 重新运行 `.\installer\start.cmd`。

### 忘记管理员密码

如果还可以访问 `.env`，修改 `ADMIN_PASSWORD` 后重启服务。重启不会删除数据。

### 需要真正的 `.exe`

当前 `installer/` 是第一版安装器基础。后续可以用 Inno Setup 或 NSIS 包装成 `.exe`，让用户双击安装；包装器只负责调用这些脚本，核心仍然通过 Docker Desktop 运行。

安装包不应提供固定默认密码，不应静默删除用户数据，也不应绕过 Docker Desktop 前置条件。
