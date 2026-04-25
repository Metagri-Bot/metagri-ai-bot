FROM python:3.13-slim

WORKDIR /app

COPY . .

ENV RAG_PROFILE=public
ENV HOST=0.0.0.0
ENV PORT=8765

RUN python ingest.py

EXPOSE 8765

CMD ["python", "app.py"]
