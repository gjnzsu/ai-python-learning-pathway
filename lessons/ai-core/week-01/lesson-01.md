# AI 应用工程核心路线 · 第 1 周 · 第 1 课：可靠的模型 API 调用器

预计用时：120–150 分钟（正文约 90 分钟，练习与小测另计）

## 本课定位

这一课是从数据分析转向 AI 应用工程的入口。我们不急着研究 Prompt 技巧，而是先解决一个更基础的问题：应用怎样可靠地调用外部模型服务。

业务场景是假设银行员工提交一个制度问题，应用把问题发送给模型 API，再把回答返回给调用方。即使模型能力很好，输入为空、密钥缺失、网络超时、服务限流或响应结构变化，都可能让整个应用失败。

本课使用普通 HTTP 接口表达这些共性，不绑定某一家模型厂商。下一课再把客户端连接到具体 LLM API，并使用 Pydantic 验证结构化输出。

## 本课目标

完成本课后，你能够：

- 解释业务请求、输入契约、HTTP 请求、JSON 响应和业务结果之间的数据流。
- 在网络调用前验证输入和配置，避免把本地错误推迟到远程服务。
- 为 HTTP 请求设置显式超时，并解释为什么默认无限等待不可接受。
- 区分输入错误、鉴权错误、限流、服务端错误、网络错误和响应格式错误。
- 判断哪些故障可以重试，哪些故障必须立即失败。
- 使用依赖注入和测试替身验证成功路径与失败边界，而不在测试中调用真实模型。
- 说明日志中可以记录什么，以及为什么不能记录密钥和敏感业务原文。

## 0. 先看完整数据流

```text
调用方
  → 创建业务请求
  → 验证输入契约
  → 读取并验证配置
  → 构造 HTTP 请求
  → 在超时边界内发送
  → 检查 HTTP 状态
  → 解析并验证 JSON
  → 返回业务结果或明确异常
```

这条链路有两个重要边界：

1. **本地边界**：输入、环境变量和请求对象是否有效。
2. **远程边界**：网络、HTTP 状态和服务响应是否符合约定。

与 Java/Spring Boot 类比，输入对象类似带校验的 DTO，客户端类似封装了 `WebClient` 的适配器，异常类型则把底层 HTTP 细节翻译为应用能够处理的失败语义。

## 1. 一个能成功、但不可靠的版本

```python
import requests


def ask_model(question: str) -> str:
    response = requests.post(
        "https://example.com/v1/chat",
        json={"question": question},
    )
    data = response.json()
    return data["answer"]
```

这段代码只描述了理想路径，至少遗漏了以下问题：

- `question` 是空白字符串怎么办？
- API 地址或密钥没有配置怎么办？
- 服务迟迟不返回怎么办？
- DNS、连接或传输临时失败怎么办？
- 服务返回 `401`、`429` 或 `500` 怎么办？
- 响应不是 JSON，或者缺少 `answer` 怎么办？

可靠性不是“永远不失败”，而是失败可预期、可分类、可测试，并且调用方知道下一步该做什么。

## 2. 用数据类定义输入和输出契约

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRequest:
    question: str

    def __post_init__(self) -> None:
        cleaned = self.question.strip()
        if not cleaned:
            raise ValueError("question 不能为空")
        if len(cleaned) > 2_000:
            raise ValueError("question 不能超过 2000 个字符")
        object.__setattr__(self, "question", cleaned)


@dataclass(frozen=True)
class ModelResult:
    answer: str
    model: str
```

`frozen=True` 使对象创建后不能通过普通赋值修改。因为输入对象被冻结，`__post_init__()` 中使用 `object.__setattr__()` 保存清理后的值。这是初始化阶段的受控规范化，不是允许业务代码随意修改对象。

输入契约解决三个问题：

- 哪些字段是必需的？
- 哪些值属于合法范围？
- 进入系统后使用原始值还是规范化后的值？

长度上限不是为了证明 2000 是普遍正确的数字，而是让资源消耗具有边界。真实系统还需要根据模型上下文窗口、检索内容、成本预算和业务需求确定限制。

## 3. 配置是另一种输入

不要把密钥写进源代码，也不要让缺失配置一直到 HTTP 请求时才暴露。

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 10.0

    @classmethod
    def from_environment(cls) -> "ApiConfig":
        base_url = os.getenv("MODEL_API_BASE_URL", "").strip()
        api_key = os.getenv("MODEL_API_KEY", "").strip()

        if not base_url:
            raise ValueError("缺少环境变量 MODEL_API_BASE_URL")
        if not api_key:
            raise ValueError("缺少环境变量 MODEL_API_KEY")

        return cls(base_url=base_url, api_key=api_key)
```

环境变量只是把配置从代码中移出，并不自动等于安全。生产环境通常应使用受控的密钥管理服务，并限制读取权限。以下内容不得写入日志：

- API 密钥和完整鉴权头。
- 未脱敏的客户身份信息。
- 账户、交易或内部制度中的敏感原文。

## 4. 用异常类型建立失败语言

如果所有失败都抛出 `Exception("调用失败")`，调用方无法判断应该重试、提示用户修改输入，还是通知运维。

```python
class ModelClientError(Exception):
    """模型客户端能够识别的基础异常。"""


class AuthenticationError(ModelClientError):
    """密钥无效或无访问权限。"""


class RateLimitError(ModelClientError):
    """服务暂时限流。"""


class TemporaryServiceError(ModelClientError):
    """网络或服务端临时故障。"""


class InvalidResponseError(ModelClientError):
    """服务响应不符合客户端契约。"""
```

异常分类是一种应用层设计。它不需要把每个底层库异常原样泄漏给调用方，而是把失败翻译成对业务有意义的类别。

| 失败 | 默认处理 | 原因 |
| --- | --- | --- |
| 空输入、超长输入 | 不重试 | 相同输入再次发送仍会失败 |
| `401`、`403` | 不重试 | 通常需要修复凭据或权限 |
| `429` | 延迟后重试 | 限流可能随时间解除，应尊重服务端退避提示 |
| `500`、`502`、`503`、`504` | 有限重试 | 服务端故障可能是暂时的 |
| 连接失败、读取超时 | 有限重试 | 网络故障可能是暂时的 |
| 非法 JSON、字段缺失 | 默认不盲目重试 | 可能是契约变化或服务持续异常 |

这里的“可重试”不等于“无限重试”。重试会增加延迟、流量和成本，还可能放大服务故障。

## 5. 实现一次调用：显式超时和响应校验

本课选择 `httpx`，因为它提供清晰的同步客户端接口，后续也能扩展到异步调用。现在先保持同步，避免同时引入并发复杂度。

```python
from collections.abc import Mapping
from typing import Any

import httpx


class ModelClient:
    def __init__(self, config: ApiConfig, http_client: httpx.Client) -> None:
        self._config = config
        self._http_client = http_client

    def ask(self, request: ModelRequest) -> ModelResult:
        try:
            response = self._http_client.post(
                f"{self._config.base_url.rstrip('/')}/v1/chat",
                headers={"Authorization": f"Bearer {self._config.api_key}"},
                json={"question": request.question},
                timeout=self._config.timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise TemporaryServiceError("模型服务暂时不可用") from error

        if response.status_code in {401, 403}:
            raise AuthenticationError("模型服务鉴权失败")
        if response.status_code == 429:
            raise RateLimitError("模型服务请求过于频繁")
        if response.status_code >= 500:
            raise TemporaryServiceError("模型服务发生服务端错误")
        if response.status_code >= 400:
            raise ModelClientError(
                f"模型服务拒绝请求，状态码 {response.status_code}"
            )

        try:
            payload: Any = response.json()
        except ValueError as error:
            raise InvalidResponseError("模型服务没有返回合法 JSON") from error

        return self._parse_result(payload)

    @staticmethod
    def _parse_result(payload: Any) -> ModelResult:
        if not isinstance(payload, Mapping):
            raise InvalidResponseError("响应 JSON 顶层必须是对象")

        answer = payload.get("answer")
        model = payload.get("model")
        if not isinstance(answer, str) or not answer.strip():
            raise InvalidResponseError("响应缺少非空字符串 answer")
        if not isinstance(model, str) or not model.strip():
            raise InvalidResponseError("响应缺少非空字符串 model")

        return ModelResult(answer=answer.strip(), model=model.strip())
```

注意这里同时存在三种结构：

1. Python 的 `ModelRequest` 业务对象。
2. 经过 JSON 编码后发送的 HTTP 请求体。
3. 远程 JSON 经校验后创建的 `ModelResult` 业务对象。

JSON 能成功解析，只能说明语法有效。`[]`、`{"answer": 123}` 和 `{"message": "ok"}` 都是合法 JSON，但不符合本客户端的响应契约。

构造函数接收 `http_client`，而不是在 `ask()` 内部直接创建客户端。这让连接生命周期可以由应用统一管理，也允许测试注入不会访问互联网的测试客户端。

## 6. 超时保护的是什么

超时不是一个笼统的“速度参数”，它保护的是有限资源：

- 用户等待时间。
- Web 服务的工作线程或协程。
- 下游连接池。
- 整条请求链路的延迟预算。

如果上游接口总预算是 15 秒，下游模型调用就不能理所当然地占满 15 秒，因为输入处理、检索、重试和结果转换也需要时间。

生产客户端常分别设置连接、读取、写入和连接池超时。本课先使用一个总配置值建立显式边界，后续再细分。

## 7. 重试策略：只重试可能自行恢复的失败

一个简单策略可以是：最多调用 3 次，第一次失败后等待 0.5 秒，第二次失败后等待 1 秒。

```python
import time
from collections.abc import Callable


def ask_with_retry(
    operation: Callable[[], ModelResult],
    *,
    max_attempts: int = 3,
    initial_delay_seconds: float = 0.5,
) -> ModelResult:
    if max_attempts < 1:
        raise ValueError("max_attempts 必须至少为 1")

    delay = initial_delay_seconds
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except (RateLimitError, TemporaryServiceError):
            if attempt == max_attempts:
                raise
            time.sleep(delay)
            delay *= 2

    raise AssertionError("循环必须返回结果或抛出异常")
```

`operation` 是一个零参数可调用对象。调用时可以写：

```python
result = ask_with_retry(lambda: client.ask(request))
```

这里的 `lambda` 只是一个匿名小函数。下面两段代码等价：

```python
def call_model() -> ModelResult:
    return client.ask(request)


result = ask_with_retry(call_model)
```

```python
result = ask_with_retry(lambda: client.ask(request))
```

直接写 `client.ask(request)` 会在进入重试函数之前立即执行；写成
`lambda: client.ask(request)` 则只保存“怎样调用”，由重试循环通过
`operation()` 决定执行时机和次数。这类似于 Java 中的
`Supplier<ModelResult>`。

还要区分“尝试次数”和“重试次数”：

```text
max_attempts = 3  → 首次调用包含在内，总共最多调用 3 次
max_retries = 3   → 如果采用这个命名，通常表示首次调用后还能重试 3 次
```

本课参数名是 `max_attempts`，因此三次连续失败只会发出三次请求，不是四次。

这个版本用于理解控制流，还不是完整生产策略。生产环境通常还需要：

- 随机抖动，避免大量实例同时再次请求。
- 尊重服务端的 `Retry-After`。
- 整体截止时间，而不只是单次超时。
- 指标记录，包括尝试次数、总延迟和最终错误类型。
- 判断操作是否具有幂等性，尤其是会产生外部副作用的工具调用。

## 8. 测试时不调用真实模型

单元测试需要快速、确定、无费用，并能精确制造错误。`httpx.MockTransport` 可以在进程内返回模拟响应。

测试替身通过构造函数注入，调用链是：

```text
client.ask(...)
  → self._http_client.post(...)
  → MockTransport
  → handler(request)
  → 模拟的 HTTP 响应
```

关键是 `httpx.Client(transport=transport)`：它用测试传输替换真实网络传输。
`ModelClient` 不需要知道自己是否处于测试环境，只使用外部传入的客户端。

```python
import httpx


def test_ask_returns_validated_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={"answer": "请查阅提前还款条款。", "model": "test-model"},
        )

    transport = httpx.MockTransport(handler)
    config = ApiConfig(
        base_url="https://model.test",
        api_key="test-key",
        timeout_seconds=1.0,
    )

    with httpx.Client(transport=transport) as http_client:
        client = ModelClient(config, http_client)
        result = client.ask(ModelRequest("如何办理提前还款？"))

    assert result == ModelResult(
        answer="请查阅提前还款条款。",
        model="test-model",
    )
```

再覆盖一个失败边界：

```python
import pytest


def test_ask_rejects_missing_answer() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"model": "test-model"})
    )
    config = ApiConfig(base_url="https://model.test", api_key="test-key")

    with httpx.Client(transport=transport) as http_client:
        client = ModelClient(config, http_client)
        with pytest.raises(InvalidResponseError, match="answer"):
            client.ask(ModelRequest("测试问题"))
```

至少应继续覆盖：

- 空问题和超长问题。
- 缺失环境变量。
- `401` 不可重试。
- `429` 可以重试，但不超过上限。
- 网络超时转换为 `TemporaryServiceError`。
- 非法 JSON、非对象 JSON、空 `answer` 和缺失 `model`。

不要在单元测试中断言真实模型必须返回某句固定自然语言。模型输出具有不确定性，真实 API 还会受到网络、版本和账户状态影响。

## 9. 本课的设计取舍

### 为什么暂时不用模型厂商 SDK

厂商 SDK 能简化鉴权、请求结构和错误处理，但也会隐藏部分 HTTP 边界。本课先用普通 HTTP 建立可迁移的心智模型。理解边界之后，再使用 SDK 会更容易判断它替我们处理了什么。

### 为什么输入先用 `dataclass`，不用 Pydantic

`dataclass` 足以展示不可变对象、初始化校验和类型标注。下一课面对模型结构化输出时再引入 Pydantic，可以清楚看到它在嵌套 Schema、类型验证和错误报告上的增量价值。

### 为什么不立即加入日志

在没有先定义数据分级和脱敏策略时，直接记录完整请求与响应可能泄漏敏感内容。首版日志只应考虑请求 ID、模型名、状态类别、延迟和尝试次数等元数据。

## 10. 课堂练习

1. 运行 `ModelRequest` 示例，观察首尾空格和空字符串分别怎样处理。
2. 为 `ApiConfig` 增加 `timeout_seconds > 0` 的验证。
3. 使用 `MockTransport` 分别制造 `401`、`429` 和 `503`，验证异常类型。
4. 让测试传入 JSON 数组 `[]`，说明“合法 JSON”为什么不等于“合法响应”。
5. 给重试函数注入一个假的等待函数，验证退避时间为 `[0.5, 1.0]`，避免测试真的等待。
6. 画出一次 `503 → 503 → 200` 调用的数据流，并计算实际 HTTP 请求次数。

## 11. 小测

1. 为什么输入校验应该发生在网络调用之前？
2. `frozen=True` 为业务请求带来什么好处？
3. 环境变量为什么比硬编码密钥好，又为什么不代表绝对安全？
4. HTTP 超时保护了哪些资源？
5. 为什么 `401` 通常不应该自动重试？
6. 为什么 `429` 可以重试，但不能立即无限重试？
7. JSON 成功解析后，为什么仍需验证字段结构？
8. `raise NewError(...) from error` 保留了什么信息？
9. 为什么测试应注入 HTTP 客户端，而不是调用真实模型服务？
10. 日志可以记录哪些调用元数据，哪些内容不应记录？

## 12. 本课验收

- [ ] 能用自己的话说明从业务输入到业务结果的数据流。
- [ ] 能解释输入错误、鉴权错误、限流和临时服务错误的处理差异。
- [ ] 客户端为每次 HTTP 调用设置显式超时。
- [ ] JSON 响应经过结构校验后才转换为业务对象。
- [ ] 只有可恢复错误进入有限重试。
- [ ] 测试不访问互联网、不使用真实密钥且不产生模型费用。
- [ ] 成功、鉴权失败、限流、服务故障和非法响应路径均有测试。
- [ ] 日志与异常消息不包含密钥或敏感业务原文。

本课完成后，下一课将把这个可靠性骨架连接到具体 LLM API，区分系统指令、用户输入和检索数据，并使用 Pydantic 定义结构化输出契约。
