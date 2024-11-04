# We will use python:3.10-alpine as the base image for building the Flask container
FROM python:3.9-slim

# It specifies the working directory where the Docker container will run
WORKDIR /app

# Copying all the application files to the working directory
COPY . .

# Install all the dependencies required to run the Flask application
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Docker container for the application to run on port 8081
EXPOSE 8081

# The command required to run the Dockerized application
CMD ["gunicorn","--config", "gunicorn_config.py", "missing_data_impute_flask_app:app"]