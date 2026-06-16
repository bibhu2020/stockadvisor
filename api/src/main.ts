import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import * as express from 'express';
import * as fs from 'fs';
import * as path from 'path';
import { AppModule, UI_DIST } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api');
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  app.enableCors({
    origin: [
      'http://localhost:5173',
      'https://mishrabp-stockadvisor.hf.space',
    ],
    credentials: true,
  });

  // Serve Vue build static assets (CSS, JS, images) before NestJS routes
  if (fs.existsSync(UI_DIST)) {
    app.use(express.static(UI_DIST));
  }

  // Initialize all NestJS routes
  await app.init();

  // SPA fallback: any request that wasn't handled by static files or API routes
  // gets index.html so Vue Router can take over client-side
  const uiIndex = path.join(UI_DIST, 'index.html');
  if (fs.existsSync(uiIndex)) {
    const server = app.getHttpAdapter().getInstance();
    server.use((_req: express.Request, res: express.Response) => {
      res.sendFile(uiIndex);
    });
  }

  const port = process.env.API_PORT ?? 3000;
  await app.listen(port);
  console.log(`StockAdvisor API running on http://localhost:${port}/api`);
}
bootstrap();
