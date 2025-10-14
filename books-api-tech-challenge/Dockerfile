# ==============================
# BASE IMAGE
# ==============================
FROM python:3.11.13-slim
WORKDIR /app

# ==============================
# INSTALL DEPENDENCIES
# ==============================
COPY requirements.txt .
RUN pip install -r requirements.txt

# ==============================
# COPY PROJECT FILES
# ==============================
COPY . .

# ==============================
# EXPOSE PORTS
# Flask will run on :5000
# Streamlit will run on :8000
# ==============================
EXPOSE 5000
EXPOSE 8000

# ==============================
# DEFAULT COMMAND
# ==============================
RUN apt-get update && apt-get install -y supervisor && mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord"]