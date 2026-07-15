# Windows Docker 运行指南

量化控制台由两个容器组成：

- `quant-backend`：Baostock 历史日线、DuckDB 缓存、回测和资金流向 API；
- `quant-web`：量化控制台网页。

## 首次准备

Docker Desktop 的 Linux 容器模式依赖 WSL 2。请以管理员身份打开 PowerShell，执行：

```powershell
wsl --install
```

按 Windows 提示重启。重启后打开 Docker Desktop，等待界面显示 Docker Engine 正在运行。

为避免 Docker 镜像和容器数据继续占满 C 盘，在 Docker Desktop 中打开：

```text
Settings > Resources > Advanced > Disk image location
```

将位置改为 E 盘，例如：

```text
E:\DockerDesktop\wsl
```

点击 Apply & Restart。不要直接移动 Docker 的 VHDX 文件。

## 启动项目

在 E 盘项目目录运行：

```powershell
.\scripts\start-docker.ps1
```

或者直接运行：

```powershell
docker compose up --build -d
```

打开量化控制台：

```text
http://127.0.0.1:8765/templates/quant-dashboard.html
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

查看容器日志：

```powershell
docker compose logs -f
```

停止服务：

```powershell
docker compose down
```

`data/market.duckdb` 是按需生成的本地行情缓存。它已被 Git 忽略，删除它只会让系统在下次查询时重新下载需要的日线数据。
