FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
COPY data ./data
ENV APP_USER=admin
ENV APP_PASSWORD=admin123
ENV APP_SECRET=change-me
ENV DATABASE_URL=sqlite:///./data/consegne.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
