# Diagram Generator Pipeline

このディレクトリには、Jenkins のパイプラインを通じて Azure/OpenAI の GPT に指示を出し、  
最新の `diagrams` ライブラリ (0.24.4) を用いてアーキテクチャ図 (PNG) を自動生成するためのスクリプト・設定を含みます。

## ファイル構成

- **Jenkinsfile**  
  Jenkinsのパイプライン定義。  
  - `DIAGRAM_REQUIREMENT` パラメータでユーザーが要望を入力  
  - Docker上で Python:3.11-slim を動かし、必要ライブラリのセットアップ後に `generate_diagram.py` を実行  
  - 生成された PNG ファイルをアーカイブ

- **generate_diagram.py**  
  Python側のメインスクリプト。  
  - GPT (例: `gpt-4o-mini`) に ChatCompletion API でプロンプトを送り、`diagram.py` (diagramsコード) を生成  
  - `diagram.py` を実行してエラーがあればエラー内容を再度 Chat API に投げ、修正されたコードを再度実行 → PNGが正常に生成されるまで繰り返す

- **requirements.txt**  
  パイプラインで `pip install -r requirements.txt` することで導入されるライブラリ。  
  - `openai==1.72.0`  
  - `diagrams==0.24.4`  

## 事前準備

1. **JenkinsのCredentials**  
   - `openai-api-key` というIDの「シークレットテキスト」を用意し、OpenAI (またはAzure OpenAI) のAPIキーを登録  
   - Jenkinsfileの `environment { OPENAI_API_KEY = credentials('openai-api-key') }` で参照

2. **Graphvizのインストール**  
   - `diagrams` は内部で Graphviz が必要になります。  
   - Jenkinsfile で `apt-get install graphviz` を実行しているため、Dockerコンテナ内で利用可能となります。  
   - カスタムのDockerイメージを使う場合はイメージに含めておくのもあり。

3. **実行方法**  
   - Jenkinsのジョブを実行し、パラメータ `DIAGRAM_REQUIREMENT` に作図要望を入力してビルド。  
   - 成功するとArtifactsに `architecture_diagram.png` がアーカイブされ、任意にダウンロードできます。  

## 注意点

- GPT連携に失敗するとパイプラインがエラーになる可能性があります。  
- `max_retry` を超えてもエラーが解消されない場合、パイプラインは失敗終了します。  
- 生成される図は GPT の応答に依存するため、必ずしも要望通りの結果になるとは限りません。細かい修正はパラメータを変更して再実行するなど工夫してください。
