# Use the official Python image as the base image
FROM python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file and install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire current directory into the container
COPY . .

# Set the environment variables
ENV TOKEN=5994782318:AAGwm1aZVE9fCMsbSPqEN55kfnxb5JKmt1Q

# Run the Python script
CMD [ "python", "bot" ]
