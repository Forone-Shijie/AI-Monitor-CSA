# 技术栈推荐矩阵（文字版 + draw.io 表格版）

本文档用于统一技术选型标准，按 **淘汰 / 不建议 / 保留 / 待研究 / 推荐** 五个等级进行分类管理。
可作为技术规范、架构治理及项目立项参考。

---

## 一、推荐等级说明

| 等级     | 含义            |
| ------ | ------------- |
| 🔴 淘汰  | 明确禁止，新老系统逐步迁移 |
| 🟡 不建议 | 原则不选，新项目避免    |
| 🔵 保留  | 存量系统允许维护      |
| 🟣 待研究 | 可进行 PoC / 试点  |
| 🟢 推荐  | 新项目优先选择       |

---

## 二、技术栈（文字版）

### 1. 后端 / Java

**🔴 淘汰**

- Struts 1.x / 2.x  
- Spring 3.x、Spring Boot 1.5.x  
- EJB、Mina  
- Tomcat 7 及以下、WebLogic、WebSphere、JBoss  
- IBM MQ  
- MySQL 5.5 及以下  
- Oracle JDK、OpenJDK 7 及以下  

**🟡 不建议**

- Zuul 1.x  
- SOAP  
- ActiveMQ  

**🔵 保留**

- Hibernate  
- RMI  
- Spring Cloud Netflix / Finchley  
- Tomcat 8.5+  
- Redis 4.x  
- PostgreSQL 9.4+  

**🟣 待研究**

- Service Mesh  
- Motan / HSF  
- Base  

**🟢 推荐**

- Spring Framework 5.x  
- Spring Boot 2.2+  
- Spring Cloud Alibaba  
- Dubbo 2.7+  
- MyBatis / MyBatis Plus  
- HikariCP  
- Redis 5+  
- RocketMQ / Kafka  
- Nacos  
- Spring Security  

---

### 2. 容器 & 云原生

**🟢 推荐**

- Docker 18+  
- Kubernetes 1.14+  
- Helm  
- Harbor  
- AdoptOpenJDK / Bisheng JDK  

---

### 3. 前端

**🔴 淘汰**

- Flash  

**🔵 保留**

- jQuery  
- AngularJS  

**🟢 推荐**

- HTML5 / CSS3  
- JavaScript / TypeScript  
- Vue.js  
- Vue Router / Vuex  
- Vant UI  
- Webpack  

---

### 4. 移动端

**Android（🟢 推荐）**

- Java / Kotlin  
- Retrofit / OkHttp  
- Gson / Glide / RxJava  
- Room / GreenDao  
- LeakCanary  
- EMAS / MPaaS  

**iOS（🟢 推荐）**

- Swift / Objective-C  
- AFNetworking  
- MVVM  
- APNS / Universal Link  
- FMDB / SQLCipher  
- EMAS / MPaaS  

---

### 5. 大数据

**🔵 保留**

- Hive  
- Spark  
- Flink  
- HDFS  

**🟢 推荐**

- MaxCompute  
- Blink  
- DataWorks / DataX / DTS  
- Quick BI  

---

## 三、draw.io 表格版本（XML，可直接导入）

使用方式：

1. 打开 https://app.diagrams.net  
2. File → Import From → Device  
3. 导入以下 XML 内容  

```xml
<mxfile host="app.diagrams.net">
  <diagram name="技术栈推荐矩阵">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <mxCell id="h1" value="分类" style="shape=rectangle;fillColor=#dae8fc;" vertex="1" parent="1">
          <mxGeometry x="0" y="0" width="160" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="h2" value="淘汰 🔴" style="shape=rectangle;fillColor=#f8cecc;" vertex="1" parent="1">
          <mxGeometry x="160" y="0" width="200" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="h3" value="不建议 🟡" style="shape=rectangle;fillColor=#fff2cc;" vertex="1" parent="1">
          <mxGeometry x="360" y="0" width="200" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="h4" value="保留 🔵" style="shape=rectangle;fillColor=#dae8fc;" vertex="1" parent="1">
          <mxGeometry x="560" y="0" width="200" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="h5" value="待研究 🟣" style="shape=rectangle;fillColor=#e1d5e7;" vertex="1" parent="1">
          <mxGeometry x="760" y="0" width="200" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="h6" value="推荐 🟢" style="shape=rectangle;fillColor=#d5e8d4;" vertex="1" parent="1">
          <mxGeometry x="960" y="0" width="240" height="40" as="geometry"/>
        </mxCell>

        <mxCell id="r1c1" value="后端 / Java" style="shape=rectangle;" vertex="1" parent="1">
          <mxGeometry x="0" y="40" width="160" height="120" as="geometry"/>
        </mxCell>
        <mxCell id="r1c2" value="Struts&#10;Spring 3.x&#10;EJB" style="shape=rectangle;fillColor=#f8cecc;" vertex="1" parent="1">
          <mxGeometry x="160" y="40" width="200" height="120" as="geometry"/>
        </mxCell>
        <mxCell id="r1c3" value="Zuul 1.x&#10;SOAP" style="shape=rectangle;fillColor=#fff2cc;" vertex="1" parent="1">
          <mxGeometry x="360" y="40" width="200" height="120" as="geometry"/>
        </mxCell>
        <mxCell id="r1c4" value="Hibernate&#10;Tomcat 8.5+" style="shape=rectangle;fillColor=#dae8fc;" vertex="1" parent="1">
          <mxGeometry x="560" y="40" width="200" height="120" as="geometry"/>
        </mxCell>
        <mxCell id="r1c5" value="Service Mesh" style="shape=rectangle;fillColor=#e1d5e7;" vertex="1" parent="1">
          <mxGeometry x="760" y="40" width="200" height="120" as="geometry"/>
        </mxCell>
        <mxCell id="r1c6" value="Spring Boot 2.2+&#10;Dubbo&#10;MyBatis&#10;Nacos" style="shape=rectangle;fillColor=#d5e8d4;" vertex="1" parent="1">
          <mxGeometry x="960" y="40" width="240" height="120" as="geometry"/>
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

---

## 四、维护建议

- 本文档应随技术演进定期更新  
- 新技术需先进入「待研究」再升级为「推荐」  
- 淘汰技术需制定迁移计划  
