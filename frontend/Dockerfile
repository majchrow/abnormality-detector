FROM node:12.19.0-alpine AS builder

WORKDIR /angular

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

EXPOSE 4200
