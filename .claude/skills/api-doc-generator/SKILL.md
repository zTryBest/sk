---
name:api-doc-generator
description:用户提供接口文档地址，采用playwright mcp服务抓取对应网页的接口文档说明，形成参考接口文档文件集合。
mcp:playwright
---

# api-doc-generator

访问指定地址网站，拉取接口文档或者功能描述信息，形成参考文档文件集合，并形成接口目录。

## 工作流总览

```
Phase 1   网站拉取
   1.1  依据网站地址，爬取有效信息
   1.2  如果页面抓取失败或者需要认证，则启动浏览器提示用户进行认证
   ▼
[Checkpoint Plan]      ← 必须停。和用户确认一些事情
                         网站 / 导航条 / 接口模块
   ▼
Phase 2   接口文档入md文件
   2.1  收集每个子模块的参考文件，放入reference文件夹中
   2.2 形成接口目录
```



工作目录约定（agent 在用户当前目录下创建 / 编辑）：

```
docs/
├── category.md          # 接口文档目录，便于查找
├── reference   # 细节参考文档目录
	├──xxx模块.md
```
