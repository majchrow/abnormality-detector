FROM node:12.19.0-alpine AS builder

WORKDIR /angular

COPY package*.json ./

RUN npm i

COPY . .

RUN npm run build

EXPOSE 4200
