# 附录D 事件列表

## 附录D1 视频事件

### 附录D.1.1 视频事件类型

| 事件分类 | 事件名称 | 事件类型码 |
| -------- | -------- | ---------- |
| 视频监控 | 视频丢失 | 131329 |
| | 视频遮挡 | 131330 |
| | 移动侦测 | 131331 |
| | 场景变更 | 131612 |
| | 虚焦 | 131613 |
| | 报警输入 | 589825 |
| | 可视域事件 | 196355 |
| | GPS采集 | 851969 |
| | 区域入侵 | 131588 |
| | 越界侦测 | 131585 |
| | 进入区域 | 131586 |
| | 离开区域 | 131587 |
| | 徘徊侦测 | 131590 |
| | 人员聚集 | 131593 |
| | 快速移动 | 131592 |
| | 停车侦测 | 131591 |
| | 物品遗留 | 131594 |
| | 物品拿取 | 131595 |
| | 人数异常 | 131664 |
| | 间距异常 | 131665 |
| | 剧烈运动 | 131596 |
| | 岗位值守 | 131603 |
| | 倒地 | 131605 |
| | 攀高 | 131597 |
| | 重点目标起身 | 131610 |
| | 人员站立 | 131666 |
| | 防风场滞留 | 131609 |
| | 起身 | 131598 |
| | 人靠近ATM | 131599 |
| | 操作超时 | 131600 |
| | 贴纸条 | 131601 |
| | 安装读卡器 | 131602 |
| | 尾随 | 131604 |
| | 声强突变 | 131606 |
| | 折线攀高 | 131607 |
| | 折线警戒面 | 131611 |
| | 温差报警 | 192518 |
| | 温度报警 | 192517 |
| | 船只检测 | 192516 |
| | 火点检测 | 192515 |
| | 烟火检测 | 192514 |
| | 烟雾检测 | 192513 |
| 视频网管 | 监控点离线 | 889196545 |

### 附录D.1.2 移动侦测报文示例

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度 | 备注 |
| -------- | -------- | -------- | -------- | -------- | ---- |
| method | String | 方法名，用于标识报文用途 | 是 | 64 | 事件固定OnEventNotify |
| params | Params | 事件参数信息 | 是 | 不限 | 具体参数信息 |

Params属性说明：

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度 | 备注 |
| -------- | -------- | -------- | -------- | -------- | ---- |
| sendTime | String | 事件从接收者（程序处理后）发出的时间 | 是 | 64 | ISO8601，示例：2018-08-15T 15:53:47.000+08:00 |
| ability | String | 事件类别 | 是 | 64 | 视频事件 |
| events | Events[] | 事件信息 | 是 | 不限 | 事件信息具体字段 |

Events属性说明：

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度 | 备注 |
| -------- | -------- | -------- | -------- | -------- | ---- |
| eventId | String | 事件唯一标识 | 是 | 64 | 同一事件若上报多次，则上报事件的eventId相同 |
| srcIndex | String | 事件源编号，物理设备是资源编号 | 是 | 64 | |
| srcType | String | 事件源类型 | 是 | 64 | |
| srcName | String | 事件源名称 | 否 | 64 | |
| eventType | Number | 事件类型 | 是 | 32 | |
| status | Number | 事件状态 | 是 | 32 | 0-瞬时 1-开始 2-停止 3-事件脉冲 4-事件联动结果更新 5-异步图片上传 |
| eventLvl | Number | 事件等级 | 否 | 32 | 0-未配置 1-低 2-中 3-高 |
| timeout | Number | 脉冲超时时间 | 是 | 32 | 单位:秒 |
| happenTime | String | 事件发生时间（设备时间） | 是 | 64 | ISO8601 |
| srcParentIndex | String | 事件发生的事件源父设备编码 | 否 | 64 | |

示例：
```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_vss",
        "events": [{
            "eventId": "0BEC42FF-105F-6D43-AC4A-C37F00A387B2",
            "eventType": 131331,
            "happenTime": "2018-08-14T07:20:51.531+08:00",
            "srcIndex": "195ecd1c1f944764b0929723ae3b4635",
            "srcName": "",
            "srcParentIndex": "f161cf4c95e1427f9e65a82edb03f642",
            "srcType": "camera",
            "status": 1,
            "timeout": 30
        }],
        "sendTime": "2018-08-14T07:20:51.531+08:00"
    }
}
```

### 附录D.1.3 视频遮挡报文示例

Events属性说明与移动侦测类似，eventType为131330。

```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_vss",
        "events": [{
            "eventId": "0BEC42FF-105F-6D43-AC4A-C37F00A387B2",
            "eventType": 131330,
            "happenTime": "2018-08-14T09:49:10.953+08:00",
            "srcIndex": "4cd411cc9fde4c8e814c86a80a869420",
            "srcName": "",
            "srcParentIndex": "07d70dc6968e4a1b8c5a79b6b49e7d57",
            "srcType": "camera",
            "status": 1,
            "timeout": 30
        }],
        "sendTime": "2018-08-14T09:49:10.954+08:00"
    }
}
```

### 附录D.1.4 视频丢失报文示例

Events属性说明与移动侦测类似，eventType为131329。

```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_vss",
        "events": [{
            "eventId": "0BEC42FF-105F-6D43-AC4A-C37F00A387B2",
            "eventType": 131329,
            "happenTime": "1900-01-00T00:00:00.000+08:00",
            "srcIndex": "f58fd21565724fb29ce16f52d7bf971a",
            "srcName": "",
            "srcParentIndex": "0289831e17a44749b790956b922e2d15",
            "srcType": "camera",
            "status": 0,
            "timeout": 0
        }],
        "sendTime": "2018-08-16T10:25:58.588+08:00"
    }
}
```

### 附录D.1.5 场景变更报文示例

Events属性说明与移动侦测类似，eventType为131612。

```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_vss",
        "events": [{
            "eventId": "0BEC42FF-105F-6D43-AC4A-C37F00A387B2",
            "eventType": 131612,
            "happenTime": "2018-08-16T14:05:14.435+08:00",
            "srcIndex": "1e9243463857424a8eac2a8ed9b267b2",
            "srcName": "",
            "srcParentIndex": "001ac7f741e34fb996a3575de35677a6",
            "srcType": "camera",
            "status": 2,
            "timeout": 30
        }],
        "sendTime": "2018-08-16T14:05:14.435+08:00"
    }
}
```

### 附录D.1.6 虚焦报文示例

Events属性说明与移动侦测类似，eventType为131613。

```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_vss",
        "events": [{
            "eventId": "0BEC42FF-105F-6D43-AC4A-C37F00A387B2",
            "eventType": 131613,
            "happenTime": "2018-08-16T14:05:14.435+08:00",
            "srcIndex": "1e9243463857424a8eac2a8ed9b267b2",
            "srcName": "",
            "srcParentIndex": "001ac7f741e34fb996a3575de35677a6",
            "srcType": "camera",
            "status": 2,
            "timeout": 30
        }],
        "sendTime": "2018-08-16T14:05:14.435+08:00"
    }
}
```

### 附录D.1.7 报警输入报文示例

Events属性说明与移动侦测类似，eventType为589825，ability为"event_io"。

```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_io",
        "events": [{
            "eventId": "0BEC42FF-105F-6D43-AC4A-C37F00A387B2",
            "eventType": 589825,
            "happenTime": "2018-08-16T14:05:14.435+08:00",
            "srcIndex": "1e9243463857424a8eac2a8ed9b267b2",
            "srcName": "",
            "srcParentIndex": "001ac7f741e34fb996a3575de35677a6",
            "srcType": "camera",
            "status": 2,
            "timeout": 30
        }],
        "sendTime": "2018-08-16T14:05:14.435+08:00"
    }
}
```

### 附录D.1.8 报警输出报文示例

Events属性说明类似，eventType为589826，ability为"event_io"。

### 附录D.1.9 可视域事件报文示例

Events属性说明增加data字段。

**Data属性说明：**

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度 | 备注 |
| -------- | -------- | -------- | -------- | -------- | ---- |
| absTime | String | 绝对时标时间戳 | 是 | 64 | 整形字符串 |
| absTimeStr | String | 绝对时标 | 是 | 64 | yyyy-MM-dd HH:mm:ss格式 |
| azimuth | String | 方位角 | 是 | 64 | 浮点型字符串，取值范围：[0.00,360.00] |
| horizontalValue | String | 水平视场角 | 是 | 64 | 浮点型字符串 |
| latitude | Coordinate | 纬度信息 | 是 | 64 | |
| latitudeType | String | 纬度类型 | 是 | 64 | 0-北纬，1-南纬 |
| longitude | Coordinate | 经度 | 是 | 64 | |
| longitudeType | String | 经度类型 | 是 | 64 | 0-东经，1-西经 |
| maxViewRadius | String | 最大可视半径 | 是 | 64 | |
| ptzPos | PtzPos | 传感器信息 | 是 | 64 | |
| sensorParam | SensorParam | 传感器信息 | 是 | 64 | |
| verticalValue | String | 垂直视场角 | 是 | 64 | |
| visibleRadius | String | 当前可视半径 | 是 | 64 | |

### 附录D.1.10 GPS采集报文示例

ability为"event_gps"，eventType为851969。

### 附录D.1.11 区域入侵事件报文示例

ability为"event_rule"，eventType为131588。

```json
{
    "method": "OnEventNotify",
    "params": {
        "ability": "event_rule",
        "events": [{
            "data": {
                "dataType": "behavioralAnalysis",
                "recvTime": "2017-04-22T15:39:01+08:00",
                "sendTime": "2017-04-22T15:39:01+08:00",
                "dateTime": "2017-04-22T15:39:01+08:00",
                "ipAddress": "10.19.134.11",
                "portNo": 80,
                "channelID": 1,
                "eventType": "fielddetection",
                "eventDescription": "fielddetection",
                "fielddetection": [{
                    "targetAttrs": {
                        "imageServerCode": "3212234",
                        "deviceIndexCode": "1568556",
                        "cameraIndexCode": "1235415",
                        "channelName": "tongdao1",
                        "cameraAddress": "杭州市西兴",
                        "longitude": 116.39737,
                        "latitude": 116.39737
                    },
                    "imageUrl": "http://10.3.1.12:8080/xxx",
                    "duration": 120,
                    "sensitivityLevel": 20,
                    "rate": 30,
                    "detectionTarget": 1,
                    "regionCoordinatesList": [{
                        "positionX": 0.901,
                        "positionY": 0.536
                    }, {
                        "positionX": 0.901,
                        "positionY": 0.536
                    }]
                }]
            },
            "eventId": "BE26E09F-0C6C-4EF9-BE2B-27007B261731",
            "eventType": 131588,
            "happenTime": "2019-01-02T15:17:24.000+08:00",
            "srcIndex": "da107dd1989e44978a5efebe73d6e979",
            "srcName": "浙江杭州",
            "srcType": "camera",
            "status": 0,
            "timeout": 0
        }],
        "sendTime": "2019-01-02T15:19:59.857+08:00"
    }
}
```

### 后续事件类型

文档中还包含了越界侦测（131585）、进入区域（131586）、离开区域（131587）、徘徊侦测（131590）、人员聚集（131593）、快速移动（131592）、停车侦测（131591）、物品遗留（131594）、物品拿取（131595）等事件的报文示例，每个事件类型的报文结构与区域入侵事件类似，主要区别在于eventType字段的值不同。
