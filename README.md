# 闲鱼自动回复管理系统

这是一个基于 Docker 部署的闲鱼自动回复和后台管理项目。别人拿到项目链接后，推荐直接用 Docker Compose 在自己电脑上部署，不需要手动安装 Python、Playwright 等复杂依赖。

项目地址：

```text
https://github.com/Mrstongtong828/xianyu-auto-0.2
```

## 一、准备环境

需要先安装：

- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Git: https://git-scm.com/downloads

Windows 用户安装 Docker Desktop 后，建议重启一次电脑，然后确认 Docker Desktop 已经启动。

## 二、部署启动

打开 PowerShell，执行：

```powershell
git clone https://github.com/Mrstongtong828/xianyu-auto-0.2.git
cd xianyu-auto-0.2
docker compose -f docker-compose-cn.yml up -d --build
```

启动完成后访问：

```text
http://localhost:8000
```

健康检查地址：

```text
http://localhost:8000/health
```

API 文档地址：

```text
http://localhost:8000/docs
```

## 三、查看运行状态

查看容器状态：

```powershell
docker compose -f docker-compose-cn.yml ps
```

查看运行日志：

```powershell
docker compose -f docker-compose-cn.yml logs --tail=100 xianyu-app
```

持续查看日志：

```powershell
docker compose -f docker-compose-cn.yml logs -f xianyu-app
```

## 四、停止和重启

停止服务：

```powershell
docker compose -f docker-compose-cn.yml down
```

重新启动：

```powershell
docker compose -f docker-compose-cn.yml up -d
```

代码更新后重新构建并启动：

```powershell
git pull
docker compose -f docker-compose-cn.yml up -d --build
```

## 五、账号和配置

项目启动后，进入后台页面完成初始化和配置。建议部署后立即修改管理员密码。

常用配置包括：

- 管理员账号和密码
- 闲鱼账号 Cookie 或登录信息
- 邮箱 SMTP 配置
- AI 回复配置
- 自动回复、自动发货、通知渠道等业务配置

不要把自己的 `.env`、数据库、Cookie、日志文件发给别人。每个人都应该在自己的电脑上配置自己的账号和密钥，避免泄露后台密码、邮箱授权码、闲鱼 Cookie 等敏感信息。

## 六、常见问题

如果 `http://localhost:8000` 打不开，先检查容器状态：

```powershell
docker compose -f docker-compose-cn.yml ps
```

如果容器没有正常启动，查看日志：

```powershell
docker compose -f docker-compose-cn.yml logs --tail=200 xianyu-app
```

如果提示端口被占用，打开 `docker-compose-cn.yml`，把：

```yaml
ports:
  - "8000:8090"
```

改成例如：

```yaml
ports:
  - "8010:8090"
```

然后重新启动：

```powershell
docker compose -f docker-compose-cn.yml up -d
```

访问地址也改为：

```text
http://localhost:8010
```

如果 Docker 构建很慢或失败，可以先确认 Docker Desktop 正常运行，并保持网络稳定后重新执行：

```powershell
docker compose -f docker-compose-cn.yml up -d --build
```

## 七、安全提醒

本项目涉及后台账号、闲鱼 Cookie、邮箱授权码等敏感信息。请只在可信电脑上部署，不要把后台直接暴露到公网。如果需要公网访问，建议配置强密码、HTTPS、反向代理和防火墙规则。

本项目仅供学习和研究使用，请遵守相关平台规则和法律法规。
