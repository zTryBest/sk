# 附录C 对象说明

## 附录C.1 门禁联网网关

### 附录C.1.1 门禁事件对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| eventID | 事件ID | DeviceIDType | | 是 | 标识了系统中唯一的事件编码 |
| personID | 人员ID | DeviceIDType | | 否 | 标识了系统中唯一的人员资源编码 |
| personName | 人员姓名 | NameType | | 否 | |
| deptID | 部门ID | DeviceIDType | | 否 | |
| deptName | 部门名称 | NameType | | 否 | |
| cardNo | 卡号 | CardNoType | | 否 | |
| doorID | 门禁点ID | DeviceIDType | | 否 | 标识了系统中唯一的门禁点资源编码 |
| doorName | 门禁点名称 | NameType | | 否 | |
| deviceID | 设备ID | DeviceIDType | | 否 | 标识了系统中唯一的设备资源编码 |
| deviceName | 设备名称 | NameType | | 否 | |
| eventTime | 时间 | DateTimeType | | 是 | 事件时间，格式：yyyyMMddhh24miss |
| eventType | 事件类型码 | EventType | | 是 | 事件类型码 |
| eventName | 事件名称 | EventNameType | | 是 | 事件名称 |
| picUrl | 抓拍图片URL | PhotoUrlType | | 否 | 事件抓拍图片URL |
| picData | 抓拍图片BASE64 | String | | 否 | 仅针对资源码AcsEventPic有效 |
| info | 备注信息 | | | 否 | 扩展消息段标签 |

### 附录C.1.2 部门对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| indexCode | 部门编号 | String | 64 | 是 | |
| externalIndexCode | 外部编码（联网编码） | String | 64 | 是 | |
| cn | 名称 | String | 256 | 是 | |
| parentIndexCode | 父级部门联网编码 | String | 64 | 是 | 最顶层的父级编号为0 |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 否 | |
| extendData | 扩展信息 | String | 512 | 否 | |
| status | 数据状态 | Integer | | 是 | 0 正常 1 删除 |

### 附录C.1.3 人员对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| indexCode | 人员编号 | String | 64 | 是 | |
| externalIndexCode | 外部编码（联网编码） | String | 64 | 是 | |
| cn | 名称 | String | 256 | 是 | |
| parentIndexCode | 父级资源编号（部门联网编码） | String | 64 | 是 | |
| deptName | 所属部门名称 | String | 256 | 是 | |
| otherName | 曾用名 | String | 64 | 否 | |
| photoUrl | 访客人员照片（证件照）地址 | String | 128 | 否 | |
| age | 年龄 | Integer | | 否 | |
| job | 职业 | String | 64 | 否 | |
| staffProperty | 职工性质 | String | 64 | 否 | |
| company | 工作单位 | String | 64 | 否 | |
| jobNo | 职工号 | String | 48 | 否 | |
| employeePost | 职位 | String | 48 | 否 | |
| employeeNumber | 员工编号 | String | 48 | 否 | |
| postType | 岗位类别 | String | 48 | 否 | |
| spouseName | 配偶姓名 | String | 256 | 否 | |
| health | 健康状况 | Integer | | 否 | |
| address | 家庭住址 | String | 64 | 否 | |
| email | 邮箱 | String | 64 | 否 | |
| phone | 电话 | String | 32 | 否 | |
| identityType | 证件类型 | IDType | 48 | 否 | |
| iDNo | 证件号码 | String | 48 | 否 | |
| iDEffectiveTime | 证件有效期起止 | String | 64 | 否 | 格式：yyyyMMdd-yyyyMMdd |
| nationality | 国籍 | String | 64 | 否 | |
| birthplace | 籍贯 | String | 64 | 否 | |
| censusRegister | 户籍 | String | 64 | 否 | |
| marriaged | 婚姻状况 | Integer | | 否 | 编码应符合GB/T 2261.2 |
| politicalStatus | 政治面貌 | String | 64 | 否 | |
| partyTime | 入党时间 | String | 64 | 否 | |
| educationBackground | 学历 | String | 64 | 否 | |
| currResidence | 现居住地 | String | 64 | 否 | |
| roomNum | 房间号 | String | 128 | 否 | |
| houseHolderRel | 与户主关系 | String | 128 | 否 | |
| studentId | 学号 | String | 16 | 否 | |
| stuStartTime | 学生入学时间 | String | | 否 | 格式为yyyy-MM-dd |
| stuEndTime | 学生毕业时间 | String | | 否 | 格式为yyyy-MM-dd |
| stuGrade | 年级 | String | 128 | 否 | |
| stuClass | 班级 | String | 128 | 否 | |
| academy | 学院 | String | 128 | 否 | |
| profession | 学生专业 | String | 128 | 否 | |
| dormitory | 宿舍楼 | String | 48 | 否 | |
| lodge | 是否住校 | Integer | | 否 | |
| personDesc | 人员描述 | String | 128 | 否 | |
| syncFlag | 同步标志 | Integer | | 否 | |
| pinyin | 拼音 | String | 64 | 否 | |
| certIssuer | 发证机构 | String | 256 | 否 | |
| certAddr | 发证地址 | String | 256 | 否 | |
| certExpireTime | 证件有效期 | String | | 否 | 格式为yyyy-MM-dd |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 是 | |
| extendData | 扩展信息 | String | 512 | 否 | |
| status | 数据状态 | Integer | | 是 | 0正常，-1删除 |

### 附录C.1.4 卡片对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| indexCode | 卡片编码（主键） | String | 64 | 是 | |
| externalIndexCode | 外部编码（联网编码） | String | 64 | 是 | |
| cn | 名称 | String | 256 | 是 | |
| parentIndexCode | 父级资源编号（人员联网编码） | String | 64 | 是 | |
| cardNo | 卡片号码 | String | 64 | 是 | |
| personId | 所属人员ID | String | 64 | 是 | |
| cardType | 卡片类型 | Integer | 4 | 是 | |
| startDate | 卡片生效日期 | DateTimeType | 64 | 是 | |
| endDate | 卡片失效日期 | DateTimeType | 64 | 是 | |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 是 | |
| extendData | 扩展信息 | String | 512 | 否 | |
| status | 数据状态 | Integer | | 是 | 0正常，-1删除 |

### 附录C.1.5 指纹对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| indexCode | 指纹编码（主键） | String | 64 | 是 | |
| externalIndexCode | 外部编码（联网编码） | String | 64 | 是 | |
| cn | 名称 | String | 256 | 是 | |
| parentIndexCode | 父级资源编号（人员联网编码） | String | 64 | 是 | |
| personID | 人员ID | String | 64 | 是 | |
| cardId | 绑定的卡片ID | String | 64 | 否 | |
| fingerModel | 指纹算法 | Integer | | 否 | 1.光学，2.电容，3.其他 |
| fingerNo | 指纹序号 | String | 64 | 是 | 手指序号，如1-10 |
| fingerprint | 指纹模组数据 | String | text | 是 | AES128加密 |
| useStatus | 使用状态 | Integer | | 是 | |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 否 | |
| extendData | 扩展信息 | String | 512 | 否 | |
| status | 数据状态 | Integer | | 是 | 0正常，-1删除 |

### 附录C.1.6 人脸对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| indexCode | 人脸编码（主键） | String | 64 | 是 | |
| externalIndexCode | 外部编码（联网编码） | String | 64 | 是 | |
| cn | 名称 | String | 256 | 是 | |
| parentIndexCode | 父级资源编号（人员联网编码） | String | 64 | 是 | |
| personId | 人员ID | String | 64 | 是 | |
| cardId | 卡片ID | String | 64 | 否 | |
| faceUrl | 人脸图片URL | String | 128 | 304000资源码必填 | 仅针对资源码304000人脸信息(URL) |
| picData | 人脸图片BASE64编码 | String | 不限 | 304001资源码必填 | 仅针对资源码304001人脸信息(图片流) |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 否 | |
| extendData | 扩展信息 | String | 512 | 否 | |
| status | 数据状态 | Integer | | 是 | 0正常，-1删除 |

### 附录C.1.7 区域对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| cn | 通用名 | String | 512 | 是 | |
| indexCode | 资源编码 | String | 64 | 是 | |
| status | 数据状态 | Integer | | 是 | 0正常，-1删除 |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 是 | |
| externalIndexCode | 组织外码编号 | String | 64 | 是 | |
| parentIndexCode | 父区域联网编码 | String | 64 | 是 | 最顶层的父级编号为0 |
| orders | 组织排序 | Integer | | 是 | |
| orgType | 组织类型 | Integer | | 否 | 0 组织、90 区域、99网关自建组织 |
| extendData | 扩展信息 | String | 512 | 否 | |

### 附录C.1.8 门禁点对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| cn | 通用名 | String | 512 | 是 | |
| indexCode | 资源编码 | String | 64 | 是 | |
| externalIndexCode | 外部编码（联网编码） | String | 64 | 是 | |
| manufacturer | 厂商 | String | 128 | 否 | |
| devModel | 设备型号 | String | 64 | 否 | |
| addr | 设备安装地址 | String | 64 | 否 | |
| block | 警区 | String | 64 | 否 | |
| parentIndexCode | 父级资源编号（区域联网编码） | String | 64 | 是 | |
| ip | ip | String | 64 | 否 | |
| port | 端口 | String | 8 | 否 | |
| password | 设备口令 | String | 8 | 否 | |
| latitude | 纬度 | String | 64 | 否 | |
| longitude | 经度 | String | 64 | 否 | |
| altitude | 海拔(单位米) | String | 64 | 否 | |
| createTime | 创建时间 | DateTimeType | 64 | 否 | |
| updateTime | 更新时间 | DateTimeType | 64 | 否 | |
| extendData | 扩展信息 | String | 512 | 否 | |
| status | 数据状态 | Integer | | 是 | 0正常，-1删除 |

### 附录C.1.9 门禁设备对象特征属性

（字段基本同门禁点，增加了secrecy保密属性字段）

### 附录C.1.10 可视对讲设备对象特征属性

增加了mainModel（主型号）、subModel（子型号）、longNum（设备编号）字段。

主型号：1-室内机; 2-门口机; 3-围墙机; 4-管理机

子型号：1-数字室内机; 2-模拟室内机; 3-单元门口机; 4-别墅门口机; 5-围墙门口机; 6-嵌入式管理机; 7-PC管理机

### 附录C.1.11 可视对讲事件对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| eventId | 事件ID | String | 64 | 是 | |
| eventType | 事件类型码 | Integer | | 是 | |
| eventName | 事件名称 | String | 64 | 是 | |
| eventTime | 时间 | String | | 是 | |
| deviceIndexCode | 设备唯一标识 | String | 64 | 否 | |
| deviceName | 设备名称 | String | 64 | 否 | |
| eventCard | 卡号 | String | 64 | 否 | |
| personId | 人员ID | String | 64 | 否 | |
| personName | 人员姓名 | String | 64 | 否 | |
| orgId | 部门ID | String | 64 | 否 | |
| orgName | 部门名称 | String | 64 | 否 | |
| picUrl | 抓拍图片URL | String | 1024 | 否 | |
| picData | 抓拍图片BASE64 | String | | 否 | 仅事件类型码800009有效 |
| extendJson | 备注信息 | String | | 否 | |
| inAndOut | 出入类型 | String | | 否 | |

### 附录C.1.12 可视对讲通话记录对象特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| eventId | 事件ID | String | 64 | 是 | |
| eventType | 事件类型码 | Integer | | 是 | 0异常通话 1接到呼叫请求 2取消呼叫 3对方正忙 4拒绝接听 5无人接听超时 6呼叫成功 7超时未挂机 8呼叫失败 |
| callId | 推送消息ID | String | 64 | 是 | |
| senderIndexCode | 呼叫方设备唯一标识 | String | 64 | 否 | |
| senderName | 呼叫方设备名称 | String | 64 | 否 | |
| receiverIndexCode | 被叫方设备唯一标识 | String | 64 | 否 | |
| receiverName | 被叫方设备名称 | String | 64 | 否 | |
| callStartTime | 呼叫起始时间 | String | | 否 | |
| callStopTime | 呼叫结束时间 | String | | 否 | |
| isConnect | 是否接通 | Integer | | 否 | 0未接通；1接通 |
| connectTime | 通话时间 | String | | 否 | |
| receiveTime | 平台接收到事件的时间 | String | | 否 | |
| info | 备注信息 | String | | 否 | |

### 附录C.1.13 访客登记信息特征属性

| 属性名称 | 属性描述 | 类型 | 长度 | 是否必填 | 备注 |
| -------- | -------- | ---- | ---- | -------- | ---- |
| visitorId | 访客id | String | 64 | 是 | |
| personName | 访客姓名 | String | 64 | 是 | |
| IdType | 证件类型 | Integer | | 否 | 符合GA/T517-2004 |
| idNo | 证件号码 | String | 64 | 否 | |
| beVisitedPersonName | 被访问人姓名 | String | 64 | 是 | |
| BeVisitedPersionId | 被访问人唯一标识 | String | | 否 | |
| BeVisitedPersonOrgId | 被访人组织标识 | String | | 否 | |
| visitorWorkUnit | 来访单位 | String | | 否 | |
| purpose | 来访事由 | String | | 否 | |
| signOrg | 证件签发机关 | String | | 否 | |
| certAddr | 证件地址 | String | | 否 | |
| birthPlace | 籍贯 | String | | 否 | |
| visitorAddress | 访客住址 | String | | 否 | |
| visitorStatus | 来访状态 | Integer | | 否 | |
| personNum | 来访人数 | Integer | | 否 | |
| startTime | 来访时间 | String | | 是 | |
| endTime | 离开时间 | String | | 否 | |
| phone | 手机号码 | String | | 否 | |
| carNo | 车牌号 | String | | 否 | |
| photoUrl | 照片URL | String | | 否 | |
| photoPicData | 图片数据流 | String | | 否 | AES128加密 |
| captureUrl | 抓拍图片URL | String | | 否 | |
| capturePicData | 抓拍数据流 | String | | 否 | AES128加密 |
| info | 备注信息 | String | | 否 | |

## 附录C.2 停车场联网网关

### 附录C.2.1 过车事件对象特征属性

| 名称 | 标识符 | 数据类型 | 长度 | 必选/可选 | 备注 |
| ---- | ------ | -------- | ---- | --------- | ---- |
| 车辆颜色 | carColor | CarColorType | | 是 | |
| 卡号 | cardNo | NameType | | 否 | |
| 出入口名称 | entranceName | NameType | | 是 | |
| 出入口ID | entranceResourcesID | DeviceIDType | | 是 | |
| 事件编号 | eventCode | | | 是 | |
| 事件ID | eventID | DeviceIDType | | 是 | |
| 过车时间 | eventTime | DateTimeType | | 是 | 格式：yyyyMMddhh24miss |
| 事件类型 | eventType | | | 是 | 524545入场事件 524546出场事件 |
| 其他信息 | info | | | 否 | |
| 是否出场 | isOut | InOutType | | 是 | |
| 主品牌 | mainLog | | | 否 | |
| 停车场名称 | parkName | NameType | | 是 | |
| 停车场编号 | parkResourcesID | DeviceIDType | | 是 | |
| 车辆图片URL | picUrl | PhotoUrlType | | 否 | |
| 车辆图片BASE64 | vehiclePicData | String | | 否 | 仅针对资源码PmsEventPic有效 |
| 车牌置信度 | plateBelieve | | | 否 | |
| 车牌颜色 | plateColor | ColorType | | 是 | |
| 车牌 | plateNo | NameType | | 是 | |
| 车牌图片URL | platePicUrl | PhotoUrlType | | 否 | |
| 车牌图片BASE64 | platePicData | String | | 否 | 仅针对资源码PmsEventPic有效 |
| 放行结果 | releaseMode | ReleaseModeType | | 否 | |
| 车道名称 | roadwayName | NameType | | 是 | |
| 车道编号 | roadwayResourcesID | DeviceIDType | | 是 | |
| 子品牌 | subLog | | | 否 | |
| 车型 | subModel | | | 否 | |
| 更新时间 | updateTime | Long | | 是 | 格式：1525244333000，毫秒 |
| 车辆类型 | vehicleType | VehicleTypeType | | 是 | |

### 附录C.2.2 - 附录C.2.11 对象特征属性

包含了部门对象、人员对象、卡片对象、指纹对象、人脸对象、区域对象、停车场对象、出入口对象、车道对象、车辆对象的特征属性，各对象的字段定义与附录C.1中对应对象类似。

## 附录C.3 资源目录

### 附录C.3.1 【区域】RegionDTO属性说明

| 属性名称 | 属性类型 | 属性描述 | 是否必填 | 备注 |
| -------- | -------- | -------- | -------- | ---- |
| indexCode | String | 区域编号 | 是 | |
| name | String | 区域名称 | 是 | |
| regionPath | String | 区域完整路径 | 是 | @进行分割，上级节点在前 |
| parentIndexCode | String | 父区域编号 | 是 | |
| available | Boolean | 用于标识区域节点是否有权限操作 | 是 | true：有权限 false：无权限 |
| leaf | Boolean | 标识区域节点是否叶子节点 | 是 | true:是叶子节点 false:不是叶子节点 |
| cascadeCode | String | 级联平台标识 | 是 | 多个级联编号以@分隔，本级区域默认值"0" |
| cascadeType | Integer | 区域标识 | 是 | 0：本级 1：级联 2：混合 |
| catalogType | Integer | 目录类型 | 是 | 0：国际区域，1：雪亮工程区域，2：司法行政区域，9：自定义区域，10：普通区域，11：级联区域，12：楼栋单元 |
| externalIndexCode | String | 外码(如：国际码) | 否 | |
| parentExternalIndexCode | String | 父外码(如：国际码) | 否 | |
| sort | Integer | 同级区域顺序 | 否 | |
| localQuantity | Integer | 本区域资源数量 | 否 | 只统计本级挂的资源数量 |
| totalQuantity | Integer | 本区域及下级区域资源数量 | 否 | 包含本级及下级 |
| createTime | String | 创建时间 | 是 | ISO8601标准 |
| updateTime | String | 更新时间 | 是 | ISO8601标准 |

### 附录C.3.2 【门禁控制器】AcsDeviceDTO属性说明

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度(Byte) | 备注 |
| -------- | -------- | -------- | -------- | -------------- | ---- |
| indexCode | String | 门禁设备唯一标识 | 是 | 64 | |
| name | String | 门禁设备名称 | 是 | 64 | |
| resourceType | String | 资源类型 | 是 | 64 | |
| deviceCode | String | 主动设备编号 | 否 | 64 | |
| devTypeCode | String | 门禁设备类型编码 | 否 | 64 | 详见附录A.7 |
| devTypeDesc | String | 门禁设备类型型号 | 否 | 64 | 详见附录A.7 |
| ip | String | 门禁设备IP | 否 | 16 | |
| manufacturer | String | 厂商 | 否 | 32 | |
| port | String | 门禁设备port | 否 | 16 | |
| description | String | 描述 | 否 | 128 | |
| regionIndexCode | String | 设备所属区域唯一标识 | 是 | 64 | |
| regionPath | String | 所属区域路径 | 是 | 340 | 根节点@子区域1@子区域2 |
| treatyType | String | 接入协议 | 否 | 32 | 详见附录A.41 |
| capability | String | 设备能力集 | 否 | 256 | 详见附录A.44 |
| cardCapacity | Integer | 设备卡容量 | 是 | | |
| fingerCapacity | Integer | 指纹容量 | 否 | | |
| veinCapacity | Integer | 指静脉容量 | 否 | | |
| faceCapacity | Integer | 人脸容量 | 否 | | |
| doorCapacity | Integer | 门容量 | 是 | | |
| parentIndexCode | String | 父级资源编号 | 否 | 64 | |
| deployId | String | 拨码 | 否 | | |
| createTime | String | 创建时间 | 是 | 64 | ISO8601标准 |
| updateTime | String | 更新时间 | 是 | 64 | ISO8601标准 |
| userId | String | 萤石的用户ID | 否 | 64 | |

### 附录C.3.3 【门禁点】DoorDTO属性说明

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度(Byte) | 备注 |
| -------- | -------- | -------- | -------- | -------------- | ---- |
| indexCode | String | 门禁点唯一标识 | 是 | 64 | |
| name | String | 门禁点名称 | 是 | 32 | |
| resourceType | String | 资源类型 | 是 | 64 | |
| doorNo | String | 门禁点编号 | 是 | 16 | |
| description | String | 描述 | 否 | 128 | |
| parentIndexCode | String | 父级资源编号 | 否 | 32 | |
| regionIndexCode | String | 所属区域唯一标识 | 是 | 64 | |
| regionPath | String | 所属区域路径 | 是 | 340 | 根节点@子区域1@子区域2 |
| channelType | String | 通道类型 | 否 | 16 | 示例：door，详见附录A.8 |
| channelNo | String | 通道号 | 否 | 16 | |
| installLocation | String | 安装位置 | 否 | 16 | |
| capability | String | 设备能力集 | 否 | 256 | 详见附录A.44，多个值以@分隔 |
| controlOneId | String | 一级控制器id | 是 | 48 | |
| controlTwoId | String | 二级控制器id | 否 | 48 | |
| readerInId | String | 读卡器1 | 是 | 48 | |
| readerOutId | String | 读卡器2 | 否 | 48 | |
| doorSerial | Integer | 门序号 | 是 | | |
| createTime | String | 创建时间 | 是 | 64 | ISO8601标准 |
| updateTime | String | 更新时间 | 是 | 64 | ISO8601标准 |

### 附录C.3.4 【门禁读卡器】AccessCardReaderDTO属性说明

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度(Byte) | 备注 |
| -------- | -------- | -------- | -------- | -------------- | ---- |
| resourceType | String | 资源类型 | 是 | 64 | |
| indexCode | String | 设备唯一标识 | 是 | 64 | |
| name | String | 设备名称 | 是 | 32 | |
| ip | String | 设备IP | 否 | 16 | |
| port | String | 设备port | 否 | 16 | |
| deviceCode | String | 主动设备编号 | 否 | 64 | |
| deviceKey | String | 设备驱动 | 否 | 64 | |
| deviceType | String | 设备系列 | 否 | 64 | |
| deviceModel | String | 设备型号 | 否 | 48 | |
| capability | String | 设备能力 | 否 | | |
| netZoneId | String | 所属网域 | 否 | 64 | |
| regionIndexCode | String | 所属区域编号 | 是 | 256 | |
| regionPath | String | 所属区域路径 | 是 | 340 | |
| dataVersion | String | 版本号 | 否 | 64 | |
| deployId | String | 拨码 | 否 | 64 | |
| communicationMode | String | 通信方式 | 是 | 64 | 0：韦根；1：RS232；2：RS485 |
| parentIndexCode | String | 父级资源编号 | 是 | 64 | |
| sort | Integer | 显示顺序 | 否 | | |
| createTime | String | 创建时间 | 是 | 64 | ISO8601标准 |
| updateTime | String | 更新时间 | 是 | 64 | ISO8601标准 |
| description | String | 描述 | 否 | 128 | |

### 附录C.3.5 【编码设备】EncodeDeviceDTO属性说明

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度(Byte) | 备注 |
| -------- | -------- | -------- | -------- | -------------- | ---- |
| belongIndexCode | String | 所属服务编号 | 否 | 64 | |
| capability | String | 能力集 | 否 | 128 | 详见附录A.44 |
| deviceKey | String | 设备驱动 | 否 | 64 | |
| deviceType | String | 设备系列 | 否 | 32 | |
| devSerialNum | String | 设备序列号 | 否 | 128 | |
| deviceCode | String | 主动设备编号 | 否 | 64 | |
| indexCode | String | 资源唯一编码 | 是 | 64 | |
| ip | String | 设备ip | 是 | 20 | |
| manufacturer | String | 厂商 | 否 | 32 | |
| name | String | 资源名称 | 是 | 32 | |
| netZoneId | String | 网域 | 否 | 32 | |
| port | String | 端口 | 是 | 32 | |
| regionIndexCode | String | 所属区域 | 是 | 64 | |
| regionPath | String | 所属区域路径 | 是 | 340 | |
| resourceType | String | 资源类型 | 是 | 32 | |
| treatyType | String | 接入协议 | 是 | 32 | 详见附录A.41 |
| createTime | String | 创建时间 | 是 | 64 | ISO8601标准 |
| updateTime | String | 更新时间 | 是 | 64 | ISO8601标准 |

### 附录C.3.6 【监控点】CameraDTO属性说明

| 参数名称 | 数据类型 | 属性描述 | 是否必填 | 最大长度(Byte) | 备注 |
| -------- | -------- | -------- | -------- | -------------- | ---- |
| indexCode | String | 监控点编号 | 是 | 64 | |
| regionIndexCode | String | 所属区域 | 是 | 64 | |
| regionPath | String | 所属区域路径 | 是 | 340 | 根节点@子区域1@子区域2 |
| externalIndexCode | String | 监控点国标编号 | 否 | 64 | |
| name | String | 监控点名称 | 是 | 64 | |
| parentIndexCode | String | 父级资源编号 | 否 | 32 | |
| longitude | String | 经度 | 否 | 32 | 精确到小数点后8位 |
| latitude | String | 纬度 | 否 | 32 | 精确到小数点后8位 |
| elevation | String | 海拔高度 | 否 | 32 | 单位：米 |
| cameraType | Integer | 监控点类型 | 是 | | 详见附录A.4 |
| installLocation | String | 安装位置 | 否 | 64 | |
| chanNum | Integer | 通道号 | 否 | | |
| cascadeCode | String | 级联编号 | 否 | 64 | |
| dacIndexCode | String | 所属DAC编号 | 否 | 64 | |
| capability | String | 设备能力集 | 否 | 256 | 详见附录A.44，多个以@分隔 |

> 注意：此文档内容来源于原始API文档，部分附录C.3章节的后续资源DTO定义（如报警输入、报警输出、IO输出、可视对讲设备等）因内容较长已做精简，详细定义请参考原始API文档。
