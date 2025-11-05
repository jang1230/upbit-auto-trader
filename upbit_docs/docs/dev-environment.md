# 개발 환경 설정 가이드

API 연동을 위한 언어별 개발 환경 설정 방법 및 주요 라이브러리를 안내합니다.

## 시작하기

업비트 API 연동 구현을 시작하기에 앞서 언어별 개발 환경을 구축 방법하는 방법을 안내합니다. Python, Java, Node.js 중 선택한 언어의 사용 환경에 대해 사용중인 OS별 가이드를 따라 개발 환경을 설정하세요.

<br />

## Python

### macOS 환경 설정

macOS에서 Python을 설치하는 방법입니다. Homebrew라는 macOS용 소프트웨어 패키지 관리자를 사용해 명령어로 간편하게 설치할 수 있습니다. 

1. **Homebrew 설치**

터미널에서 다음 명령어를 실행해 Homebrew를 설치합니다.

```shell
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

<br />

설치를 완료하고 터미널에서 다음 명령어를 실행해 Homebrew의 버전을 확인합니다. 

```shell
brew -v

Homebrew 4.6.1
```

<br />

2. **Python 설치**

터미널에서 다음 명령어를 실행해 Python을 설치합니다. Homebrew를 사용해 Python을 설치합니다.

```shell
brew install python
```

<br />

설치를 완료하고 터미널에서 다음 명령어를 실행해 Python의 버전을 확인합니다. 정상적으로 설치를 완료한 경우 Python의 버전을 확인할 수 있습니다.

```shell
python3 --version

Python 3.13.2
```

<br />

3. **가상 환경 설정**

프로젝트별 의존성 충돌 방지를 위해 가상 환경을 사용합니다.

```shell
python3 -m venv .venv

source .venv/bin/activate
```

<br />

정상적으로 가상 환경이 활성화된 경우, 프롬프트에 (venv)가 표시됩니다.

```shell
(.venv) user@computer:~/project$
```

가상 환경 내에서 개발 환경에 따라 필요한 package를 자유롭게 설치할 수 있으며, 이 때 설치된 package들은 글로벌 환경에 변경을 주지 않으므로 편리하게 프로젝트별 의존성 관리를 수행할 수 있습니다.

개발을 완료한 후 터미널에서 다음 명령어를 실행해 가상 환경을 비활성화할 수 있습니다.

```shell
deactivate
```

<br />

### Windows 환경 설정

1. **Python 공식 웹사이트에서 설치 파일 다운로드**

Windows 운영체제에서 Python을 사용하기 위해서는 Python 공식 웹사이트에서 제공하는 설치 파일을 다운로드해야 합니다. 아래 링크를 클릭해 공식 웹사이트를 방문하고 설치 파일을 다운로드하세요. 설치 과정에서** [Add Python to PATH] **옵션을 선택하면 별도의 환경 변수 설정 없이 Python을 바로 사용할 수 있습니다.

- [Python 다운로드 바로가기](https://www.python.org/downloads/) 

<br />

2. **가상 환경 설정**

Python은 프로젝트간 충돌을 방지하고 의존성을 관리하기 위해 가상 환경을 구성해 개발 환경을 관리합니다. Python을 설치한 후 터미널에 다음 명령어를 실행해 가상 환경을 구성하고 활성화할 수 있습니다.

```shell
python -m venv .venv

.venv\Scripts\activate
```

<br />

개발을 완료한 후 터미널에서 다음 명령어를 실행해 가상 환경을 비활성화할 수 있습니다

```shell
deactivate
```

<br />

### HTTP 클라이언트 라이브러리 안내

REST API와 WebSocket을 호출하기 위해 사용할 수 있는 대표적인 HTTP 클라이언트 라이브러리를 소개합니다. 

#### REST API - `requests` 라이브러리

1. **설치**

```shell
pip install requests
```

<br />

2. **기본 사용법**

```python
import requests

url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"
response = requests.get(url)
data = response.json()
print(data[0]["trade_price"])  
```

- GET, POST 등 다양한 HTTP 요청을 쉽게 보낼 수 있습니다.

<br />

#### WebSockets - 'websocket-client', 'websockets' 라이브러리

각각 동기 방식의 WebSocket 연결, 비동기 방식의 WebSocket 연결을 위한 라이브러리입니다. 개발 환경에 맞게 선택하여 사용하실 수 있습니다. 

<br />

1. **설치**

```shell
pip install websocket-client
pip install websockets
```

<br />

2. **기본 사용법 **

```python
import websocket # websocket-client
import json

def on_message(ws, message):
    print("Received:", message)

ws = websocket.WebSocketApp(
    "wss://api.upbit.com/websocket/v1",
    on_message=on_message
)

subscribe_message = [
    {"ticket":"test"},
    {"type":"ticker","codes":["KRW-BTC"]}
]

def on_open(ws):
    ws.send(json.dumps(subscribe_message))

ws.on_open = on_open
ws.run_forever(ping_interval=30, ping_timeout=10, reconnect=2)
```

- 콜백 함수(on_message)를 통해 서버로부터 받은 메시지를 처리할 수 있습니다.
- WebSocket 연결 관리 및 이벤트 처리를 위해 on_open, on_close, on_error 등의 콜백 함수를 함께 구현할 수 있습니다.
  - on_open: 서버 연결 직후 구독 메시지 전송 등 초기 작업 처리
  - on_close: 연결 종료 시 리소스 정리, 재연결 로직 등 구현 가능
  - on_error: 네트워크 오류 등 예외 상황 대응
- 인증이 필요한 /private WebSocket 연결 시에는 Header에 인증 정보를 포함해야 합니다. 아래 Recipe를 참고하여 구현할 수 있습니다.

[block:tutorial-tile]
{
  "backgroundColor": "#ffffff",
  "emoji": "🔌",
  "id": "68ef7ce9a70441b7732390a9",
  "link": "https://docs.upbit.com/v1.6.0/recipes/python-websocket-연결",
  "slug": "python-websocket-연결",
  "title": "[Python] Websocket 연결"
}
[/block]


<br />

***

## Java

### IDE(IntelliJ IDEA) 환경 설정

IntelliJ IDEA는 JetBrains에서 개발한 통합 개발 환경으로 Java와 Kotlin 개발 환경에서 널리 사용됩니다. 이 가이드에서는 IntelliJ IDEA를 사용해 Java 개발 환경을 구축합니다. 

1. **IntelliJ IDEA 설치**  
   JetBrains 공식 웹사이트에서 IntelliJ IDEA를 설치할 수 있습니다. JetBrains은 Community Edition(무료), Ultimate(유료) 등 2가지 버전의 IntelliJ IDEA를 제공합니다. 사용자의 목적에 맞는 버전을 선택해 설치합니다. 
   - [IntelliJ IDEA 다운로드 바로가기](http://jetbrains.com/idea/download)  
     <br />
2. **JDK 설치**  
   Java 개발 환경을 구축하기 위해 JDK(Java Development Kit)를 설치합니다. Amazon, IBM, Microsoft 등 다양한 기관에서 OpenJDK를 제공하고 있으며 사용 환경, 요구 사항에 따라 가장 적합한 배포판을 선택해 설치합니다. 

<br />

3. **IntelliJ IDEA 설정**
   - IntelliJ IDEA를 실행하고 기존 프로젝트를 열거나 새로운 프로젝트를 생성합니다.  
     <br/>
   - 상단 메뉴에서 File > Project Structure를 클릭합니다.  
     <br/>
   - Project Structure 창의 좌측 메뉴에서 Platform Settings > SDKs를 선택합니다.  
     <br/>
   - 설치한 JDK가 목록에 없다면 상단의 + 버튼을 클릭하고 [Add JDK] 버튼을 클릭합니다.  
     <br/>
   - JDK 설치 경로를 선택합니다. 운영체제별 일반적인 JDK 설치 경로는 다음과 같습니다.
     - macOS: `/Library/Java/JavaVirtualMachines/<jdk-version>/Contents/Home`
     - Windows: `C:\Program Files\Java\<jdk-version>`  
       <br/>
   - 올바르게 경로를 선택하면 IntelliJ IDEA가 자동으로 JDK를 인식해 추가합니다.  
     <br/>
   - Project Structure 창 좌측 메뉴에서 Project를 선택합니다.  
     <br/>
   - 오른쪽 화면의 Project SDK 드롭다운 메뉴에서 추가한 JDK를 선택합니다.  
     <br/>
   - Language level을 프로젝트에 맞는 Java 버전으로 선택합니다.  
     <br/>
   - 설정 변경 완료 후 우측 하단의 [OK] 버튼 또는 [Apply] 버튼을 클릭해 설정을 저장하고 창을 닫습니다.

<br />

4\.**Java 환경 설정 테스트**  
JDK 설정을 확인하기 위해 간단한 Java 클래스 코드를 작성해 테스트합니다. 

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, Java!");
    }
}
```

실행 후 다음과 같은 결과가 출력되면 JDK 설정이 올바르게 완료된 것을 확인할 수 있습니다.

```
Hello, Java!
```

<br />

### HTTP 클라이언트 라이브러리 안내

REST API와 WebSocket을 Java에서 호출하기 위한 대표적인 HTTP 클라이언트 라이브러리들을 소개합니다. 개발 환경 및 Framework에 따라 적합한 라이브러리를 선택하여 사용하십시오.

<br />

#### 라이브러리별 특징 및 설치 방법

1. **OkHttp **

OkHttp는 널리 사용되는 Java/Android HTTP 클라이언트로, REST API와 WebSocket 통신 모두 지원합니다. 경량이면서 비동기 및 동기 요청 모두 지원하고, 다양한 커스텀 설정에 용이합니다. 아래와 같이 설치 의존성을 설정하거나 직접 다운로드 받을 수 있습니다.

```Text Gradle
implementation 'com.squareup.okhttp3:okhttp:{version}'
```
```Text Maven
<dependency>
  <groupId>com.squareup.okhttp3</groupId>
  <artifactId>okhttp</artifactId>
  <version>{version}</version>
</dependency>
```

REST API 호출 및 WebSocket 연결 예제는 아래와 같습니다.

```java REST API
OkHttpClient client = new OkHttpClient();

Request request = new Request.Builder()
  	.url("https://api.upbit.com/v1/ticker?markets=KRW-BTC")
		.addHeader("accept", "application/json")
    .build();

try (Response response = client.newCall(request).execute()) {
    System.out.println(response.body().string());
}
```
```java WebSocket
import okhttp3.*;

OkHttpClient client = new OkHttpClient();

Request request = new Request.Builder()
    .url("wss://api.upbit.com/websocket/v1")
    .build();

WebSocketListener listener = new WebSocketListener() {
    @Override
    public void onOpen(WebSocket webSocket, Response response) {
        String subscribeMessage = "[{\"ticket\":\"test\"},{\"type\":\"ticker\",\"codes\":[\"KRW-BTC\"]}]";
        webSocket.send(subscribeMessage);
    }
    @Override
    public void onMessage(WebSocket webSocket, String text) {
        System.out.println("Received: " + text);
    }
    @Override
    public void onClosed(WebSocket webSocket, int code, String reason) {
        System.out.println("Closed: " + reason);
    }
    @Override
    public void onFailure(WebSocket webSocket, Throwable t, Response response) {
        t.printStackTrace();
    }
};
client.newWebSocket(request, listener);
client.dispatcher().executorService().shutdown();
```

<br />

2. **Spring WebClient**

Spring WebClient는 Spring 5부터 제공되는 Reactive HTTP/WebSocket 클라이언트입니다. 비동기 및 스트림 기반 처리에 최적화되어 있어 대용량, 고성능 API 연동에 적합합니다. Spring Boot 2.0 이상을 사용하는 경우 REST, WebSocket 모두 손쉽게 사용할 수 있습니다. 아래와 같이 설치 의존성을 설정하거나 직접 다운로드 받을 수 있습니다.

```Text Gradle
implementation 'org.springframework.boot:spring-boot-starter-webflux'
```
```Text Maven
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
```

REST API 호출 및 WebSocket 연결 예제는 아래와 같습니다

```java REST API
import org.springframework.web.reactive.function.client.WebClient;

WebClient client = WebClient.create();
String response = client.get()
  	.uri("https://api.upbit.com/v1/ticker?markets=KRW-BTC")
		.header("accept", "application/json") 
    .retrieve()
    .bodyToMono(String.class)
    .block();
System.out.println(response);
```
```java WebSocket
import org.springframework.web.reactive.socket.client.ReactorNettyWebSocketClient;
import org.springframework.web.reactive.socket.WebSocketHandler;
import org.springframework.web.reactive.socket.WebSocketSession;
import reactor.core.publisher.Mono;

import java.net.URI;

ReactorNettyWebSocketClient client = new ReactorNettyWebSocketClient();
client.execute(
        URI.create("wss://api.upbit.com/websocket/v1"),
        session -> session.send(
                Mono.just(session.textMessage(
                        "[{\"ticket\":\"test\"},{\"type\":\"ticker\",\"codes\":[\"KRW-BTC\"]}]"
                ))
            ).thenMany(session.receive()
                .map(msg -> {
                    System.out.println("Received: " + msg.getPayloadAsText());
                    return msg;
                })
            ).then()
).block();
```

<br />

3. **Retrofit**

Retrofit은 OkHttp 기반의 REST API 클라이언트로, 인터페이스로 API 명세를 정의한 뒤 gson 라이브러리와 함께 사용하여 DTO 자동 매핑, 비동기 호출 등을 쉽게 구현할 수 있습니다. 응답을 객체로 역직렬화하거나, API 명세 관리가 중요한 프로젝트에 유용합니다. WebSocket은 직접 지원하지 않으나 OkHttp를 기반으로 하는 라이브러리이므로 OkHttp의 WebSocket 기능을 활용할 수 있습니다.

```Text Gradle
implementation 'com.squareup.retrofit2:retrofit:2.11.0'
implementation 'com.squareup.retrofit2:converter-gson:2.11.0'
```
```Text Maven
<dependency>
  <groupId>com.squareup.retrofit2</groupId>
  <artifactId>retrofit</artifactId>
  <version>2.11.0</version>
</dependency>
<dependency>
  <groupId>com.squareup.retrofit2</groupId>
  <artifactId>converter-gson</artifactId>
  <version>2.11.0</version>
</dependency>
```

REST API 호출 예제는 아래와 같습니다.

```java
import retrofit2.Call;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;
import retrofit2.http.GET;
import retrofit2.http.Query;

import java.util.List;
import java.util.Map;

public interface UpbitService {
  	@GET("v1/ticker")
		@Headers("accept: application/json")
    Call<List<Map<String, Object>>> getTicker(@Query("markets") String markets);
}

Retrofit retrofit = new Retrofit.Builder()
    .baseUrl("https://api.upbit.com/")
    .addConverterFactory(GsonConverterFactory.create())
    .build();

UpbitService service = retrofit.create(UpbitService.class);
Call<List<Map<String, Object>>> call = service.getTicker("KRW-BTC");
List<Map<String, Object>> response = call.execute().body();
System.out.println(response);
```

<br />

4. **Java 표준 HttpClient (Java 11+)**

Java 11 이상에서 내장되는 표준 HTTP 클라이언트로, 별도의 외부 라이브러리 설치 없이 REST API 연동이 가능합니다. HTTP/2, 비동기, 동기 모두 지원하며 간단한 REST 연동 시 간편하게 사용할 수 있습니다. WebSocket도 지원하나 사용법은 상대적으로 복잡합니다.

```java REST API
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
  	.uri(URI.create("https://api.upbit.com/v1/ticker?markets=KRW-BTC"))
		.header("accept", "application/json")
    .build();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.body());
```
```java WebSocket
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.util.concurrent.CompletionStage;

HttpClient client = HttpClient.newHttpClient();
WebSocket webSocket = client.newWebSocketBuilder()
    .buildAsync(URI.create("wss://api.upbit.com/websocket/v1"), new WebSocket.Listener() {
        @Override
        public void onOpen(WebSocket webSocket) {
            String subscribeMessage = "[{\"ticket\":\"test\"},{\"type\":\"ticker\",\"codes\":[\"KRW-BTC\"]}]";
            webSocket.sendText(subscribeMessage, true);
            WebSocket.Listener.super.onOpen(webSocket);
        }
        @Override
        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
            System.out.println("Received: " + data);
            return WebSocket.Listener.super.onText(webSocket, data, last);
        }
        @Override
        public void onError(WebSocket webSocket, Throwable error) {
            error.printStackTrace();
        }
    }).join();
```

<br />

***

<br />

## Node.js

### macOS 환경 설정

MacOS에서 Node.js를 설치하는 방법입니다. Homebrew라는 MacOS용 소프트웨어 패키지 관리자를 사용해 명령어로 간편하게 설치할 수 있습니다.

1. **Homebrew 설치**

```shell
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

설치를 완료하고 터미널에서 다음 명령어를 실행해 Homebrew의 버전을 확인합니다. 정상적으로 설치를 완료한 경우, Homebrew의 버전을 확인할 수 있습니다.

```shell
brew -v

Homebrew 4.5.3
```

<br />

2. **NVM 설치**

```shell
brew install nvm
```

NVM 설치 후, 쉘 프로필에 환경 변수를 추가합니다. 터미널에서 다음 명령어를 실행합니다.

- zsh 사용자

```shell
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.zshrc
echo '[ -s "$(brew --prefix nvm)/nvm.sh" ] && source "$(brew --prefix nvm)/nvm.sh"' >> ~/.zshrc
```

- bash 사용자

```shell
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.bash_profile
echo '[ -s "$(brew --prefix nvm)/nvm.sh" ] && source "$(brew --prefix nvm)/nvm.sh"' >> ~/.bash_profile
```

<br />

쉘 프로필을 업데이트하고 터미널에서 다음 명령어를 실행해 설정을 반영합니다. 

- zsh 사용자

```shell
source ~/.zshrc
```

- bash 사용자

```shell
source ~/.bash_profile
```

<br />

 설정을 반영하고 터미널에서 다음 명령어를 실행해 NVM의 버전을 확인합니다. 정상적으로 설치를 완료한 경우 NVM의 버전을 확인할 수 있습니다.

```shell
nvm --version

0.40.1
```

<br />

3. **Node.js 설치** 

```shell
nvm install <version>

nvm install --lts
```

<br />

Node.js를 설치한 후 터미널에서 다음 명령어를 실행해 Node.js의 버전을 확인합니다. 정상적으로 설치를 완료한 경우 Node.js의 버전을 확인할 수 있습니다.

```shell
node -v

v22.14.0
```

<br />

### Windows 환경 설정

1. **Node.js 공식 웹사이트에서 설치 파일 다운로드**

Windows 운영체제에서 Node.js를 사용하기 위해서는 Node.js 공식 웹사이트에서 제공하는 설치 파일을 다운로드 받아야 합니다. 아래 링크를 클릭해 공식 웹사이트를 방문하고 설치 파일을 다운로드하세요. 설치 과정에서** [Add to PATH] **옵션이 기본적으로 설정되어 있습니다. 이 옵션을 사용하는 경우 별도의 환경 변수 설정 없이 Node.js를 바로 사용할 수 있습니다.

- [Node.js 다운로드 바로가기](https://nodejs.org/ko/download) 

<br />

Node.js를 설치한 후 터미널에서 다음 명령어를 실행해 Node.js의 버전을 확인합니다. 정상적으로 설치를 완료한 경우 Node.js의 버전을 확인할 수 있습니다.

```shell
node -v

v22.14.0
```

<br />

### HTTP 클라이언트 라이브러리 안내

Node.js 환경에서 REST API와 WebSocket을 호출하기 위해 사용할 수 있는 대표적인 라이브러리입니다.

#### REST API - `Axios` 라이브러리

Axios는 가장 널리 쓰이는 Promise 기반의 HTTP 클라이언트 라이브러리입니다. RESTful API 호출에 최적화되어 있으며 간결한 문법과 다양한 환경(브라우저, Node.js) 지원이 특징입니다. 다음과 같이 설치합니다.

```shell
npm install axios
```

REST API 호출 예제는 아래와 같습니다.

```javascript
const axios = require('axios');

axios.get('https://api.upbit.com/v1/ticker', {
  params: { markets: 'KRW-BTC' },
  headers: { 'accept': 'application/json' }
})
.then(response => {
  console.log(response.data[0].trade_price);
})
.catch(error => {
  console.error(error);
});
```

<br />

#### WebSocket - `ws` 라이브러리

ws는 Node.js에서 가장 널리 쓰이는 WebSocket 클라이언트/서버 구현 라이브러리입니다. 실시간 데이터 제공 API에 적합하며 이벤트 기반으로 메시지를 주고받을 수 있습니다. 다음과 같이 설치합니다.

```shell
npm install ws
```

WebSocket 사용 예시는 아래와 같습니다.

```javascript
const WebSocket = require('ws');

const ws = new WebSocket('wss://api.upbit.com/websocket/v1', {
  headers: {
    'accept': 'application/json'
  }
});

ws.on('open', () => {
  const subscribeMessage = [
    { ticket: 'test' },
    { type: 'ticker', codes: ['KRW-BTC'] }
  ];
  ws.send(JSON.stringify(subscribeMessage));
});

ws.on('message', (data) => {
  console.log('Received:', data.toString());
});

ws.on('close', () => {
  console.log('WebSocket connection closed');
});

ws.on('error', (error) => {
  console.error('WebSocket error:', error);
});
```