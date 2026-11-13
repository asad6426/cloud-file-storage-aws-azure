FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --uid 10001 --no-create-home app
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY cloudfiles ./cloudfiles
USER 10001
EXPOSE 8000
CMD ["gunicorn", "cloudfiles.api:create_app()", "--bind", "0.0.0.0:8000"]
