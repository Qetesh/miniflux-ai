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
- **LLM**: Model settings, API key, and endpoint.Add timeout, max_workers parameters due to multithreading
- **Agents**: Define each agent's prompt, allow_list/deny_list filters, and output style（`style_block` parameter controls whether the output is formatted as a code block in Markdown）.

Example `config.yml`:
```yaml
# INFO、DEBUG、WARN、ERROR
log_level: "INFO"

miniflux:
  base_url: https://your.server.com
  api_key: Miniflux API key here

llm:
  base_url: http://host.docker.internal:11434/v1
  api_key: ollama
  model: llama3.1:latest
#  timeout: 60
#  max_workers: 4

agents:
  summary:
    title: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17.777 14.283" width="17.777" height="14.283"> <style> path { fill: #4b4b4b; } @media (prefers-color-scheme: dark) { path { fill: #d0d0d0; } } </style> <g fill="#d0d0d0" fill-opacity="1" transform="translate(2.261,-1.754)"> <path d="M-2.261 3.194v6.404c0 1.549 0.957 4.009 4.328 4.188h9.224l0.061 1.315c0.04 0.882 0.663 1.222 1.205 0.666l2.694-2.356c0.353-0.349 0.353-0.971 0-1.331L12.518 10.047c-0.525-0.524-1.205-0.196-1.205 0.665v1.091H2.257c-0.198 0-2.546 0.221-2.546-2.911V3.194c0-0.884-0.362-1.44-0.99-1.44-1.106 0-0.956 1.439-0.982 1.44z"/> </g> <path d="M5.679 1.533h8.826c0.421 0 0.753-0.399 0.755-0.755 0.002-0.36-0.373-0.774-0.755-0.774H5.679c-0.536 0-0.781 0.4-0.781 0.764 0 0.418 0.289 0.764 0.781 0.764zm0 4.693h4.502c0.421 0 0.682-0.226 0.717-0.742 0.03-0.44-0.335-0.787-0.717-0.787H5.679c-0.402 0-0.763 0.214-0.781 0.71-0.019 0.535 0.379 0.818 0.781 0.818z" fill="#d0d0d0"/> </svg> AI 摘要'
    prompt: "Please summarize the content of the article under 50 words in Chinese. Do not add any additional Character、markdown language to the result text. 请用不超过50个汉字概括文章内容。结果文本中不要添加任何额外的字符、Markdown语言。"
    style_block: true
    deny_list:
      - https://xxxx.net
    allow_list:

  translate:
    title: "🌐AI 翻译"
    prompt: "You are a highly skilled translation engine with expertise in the news media sector. Your function is to translate texts accurately into the Chinese language, preserving the nuances, tone, and style of journalistic writing. Do not add any explanations or annotations to the translated text."
    style_block: false
    deny_list:
    allow_list:
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

## Roadmap
- [ ] Add daily summary(by title, Summary of existing AI)
  - [ ] Add Morning and Evening News（e.g. 9/24: AI Morning News, 9/24: AI Evening News）
  - [ ] Add timed summary

## Contributing

Feel free to fork this repository and submit pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License.
