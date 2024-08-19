# miniflux-ai
Miniflux with AI

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/472306c8-cdd2-4325-8655-04ba7e6045e5">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/user-attachments/assets/ae99a06f-47b4-4de7-9373-4b82f5102b7e">
  <img align="right" alt="miniflux UI" src="https://github.com/user-attachments/assets/ae99a06f-47b4-4de7-9373-4b82f5102b7e" width="400" > 
</picture>

This project fetches RSS subscription content from Miniflux via API and utilizes a large language model (LLM) to generate summaries, translations, etc. The configuration file allows for easy customization and addition of LLM agents.

## Features

- **Miniflux Integration**: Seamlessly fetch unread entries from Miniflux.
- **LLM Processing**: Generate summaries, translations, etc. based on your chosen LLM agent.
- **Flexible Configuration**: Easily modify or add new agents via the `config.yml` file.
- **Markdown and HTML Support**: Outputs in Markdown or styled HTML blocks, depending on configuration.

## Requirements

- Python 3.11+
- Dependencies: Install via `pip install -r requirements.txt`
- Miniflux API Key
- API Key compatible with OpenAI-compatible LLMs (e.g., Ollama for LLaMA 3.1)

## Configuration

The repository includes a template configuration file: `config.sample.yml`. Modify the `config.yml` to set up:

- **Miniflux**: Base URL and API key.
- **LLM**: Model settings, API key, and endpoint.
- **Agents**: Define each agent's prompt, whitelist/blacklist filters, and output style（`style_block` parameter controls whether the output is formatted as a code block in Markdown）.

Example `config.yml`:
```yaml
miniflux:
  base_url: https://your.server.com
  api_key: Miniflux API key here

llm:
  base_url: http://host.docker.internal:11434/v1
  api_key: ollama
  model: llama3.1:latest

agents:
  summary:
    title: "💡AI 摘要"
    prompt: "Please summarize the content of the article under 50 words in Chinese. Do not add any additional Character、markdown language to the result text. 请用不超过50个汉字概括文章内容。结果文本中不要添加任何额外的字符、Markdown语言。"
    style_block: true
    blacklist:
      - https://xxxx.net
    whitelist:
  translate:
    title: "🌐AI 翻译"
    prompt: "You are a highly skilled translation engine with expertise in the news media sector. Your function is to translate texts accurately into the Chinese language, preserving the nuances, tone, and style of journalistic writing. Do not add any explanations or annotations to the translated text."
    style_block: false
    blacklist:
    whitelist:
      - https://www.xxx.com/
```

## Docker Setup

The project includes a `docker-compose.yml` file for easy deployment:

```yaml
version: '3.3'
services:
    miniflux_ai:
        container_name: miniflux_ai
        image: ghcr.io/qetesh/miniflux-ai:latest
        restart: always
        environment:
            TZ: Asia/Shanghai
        volumes:
            - ./config.yml:/app/config.yml
```

To start the service, run:

```bash
docker-compose up -d
```

## Usage

1. Ensure `config.yml` is properly configured.
2. Run the script: `python main.py`
3. The script will fetch unread RSS entries, process them with the LLM, and update the content in Miniflux.

## Contributing

Feel free to fork this repository and submit pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License.
