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

  const uiIndex = path.join(UI_DIST, 'index.html');
  if (fs.existsSync(UI_DIST)) {
    // Static assets (CSS, JS, images) — runs before NestJS router
    app.use(express.static(UI_DIST));
  }
  if (fs.existsSync(uiIndex)) {
    // SPA fallback: non-API paths get index.html so Vue Router handles them.
    // Must be registered before app.listen() (which triggers app.init() and
    // registers NestJS's router) so it sits in front of NestJS's 404 handler.
    app.use((req: express.Request, res: express.Response, next: express.NextFunction) => {
      if (req.path.startsWith('/api')) return next();
      res.sendFile(uiIndex);
    });
  }

  const port = process.env.API_PORT ?? 3000;
  await app.listen(port);
  console.log(`StockAdvisor API running on http://localhost:${port}/api`);
}
bootstrap();
