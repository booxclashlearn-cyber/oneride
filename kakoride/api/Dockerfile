FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY kakoride/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY kakoride/api /app/kakoride/api
RUN useradd --create-home appuser
USER appuser
ENV KAKORIDE_ENVIRONMENT=production KAKORIDE_STORAGE=firestore
CMD ["sh", "-c", "exec uvicorn kakoride.api.app:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
