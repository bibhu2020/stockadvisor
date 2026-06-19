import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import * as path from 'path';

// pg returns TIMESTAMP WITHOUT TIME ZONE (OID 1114) as a bare string like
// "2026-06-19 14:45:00.123456" with no timezone indicator.  Node's Date
// constructor treats that as *local* time, baking the server's TZ offset
// into the serialised JSON before the browser ever sees it.
// Force both timestamp OIDs to be parsed as UTC so the stored value is
// faithfully preserved — Python always writes utcnow() (UTC, naive).
// eslint-disable-next-line @typescript-eslint/no-require-imports
const pgTypes = require('pg').types;
pgTypes.setTypeParser(1114, (v: string) => (v ? new Date(v.replace(' ', 'T') + 'Z') : null));
pgTypes.setTypeParser(1184, (v: string) => (v ? new Date(v) : null));
import { SqliteDateSubscriber } from './common/sqlite-date.subscriber';
import { AgentRunsModule } from './agent-runs/agent-runs.module';
import { AuthModule } from './auth/auth.module';
import { AgentRun } from './common/entities/agent-run.entity';
import { AnalystReport } from './common/entities/analyst-report.entity';
import { Notification } from './common/entities/notification.entity';
import { PortfolioSnapshot } from './common/entities/portfolio-snapshot.entity';
import { Position } from './common/entities/position.entity';
import { Setting } from './common/entities/setting.entity';
import { Strategy } from './common/entities/strategy.entity';
import { Transaction } from './common/entities/transaction.entity';
import { User } from './common/entities/user.entity';
import { DashboardModule } from './dashboard/dashboard.module';
import { NotificationsModule } from './notifications/notifications.module';
import { PortfolioModule } from './portfolio/portfolio.module';
import { ReportsModule } from './reports/reports.module';
import { SettingsModule } from './settings/settings.module';
import { StrategiesModule } from './strategies/strategies.module';
import { TransactionsModule } from './transactions/transactions.module';
import { UsersModule } from './users/users.module';

// Resolve root .env whether running from api/ (dev) or project root (prod)
const ROOT_DIR = path.resolve(__dirname, '..', '..'); // api/dist → project root
const ENV_PATH = path.join(ROOT_DIR, '.env');

export const UI_DIST = path.join(ROOT_DIR, 'ui', 'dist');

const ENTITIES = [
  User, Setting, Strategy, AgentRun, AnalystReport,
  Position, Transaction, PortfolioSnapshot, Notification,
];

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, envFilePath: ENV_PATH }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => {
        const url = cfg.get<string>('DATABASE_URL');
        if (url && url.startsWith('postgresql')) {
          // Neon PostgreSQL — strip channel_binding which pg driver doesn't support
          const cleanUrl = url
            .replace('&channel_binding=require', '')
            .replace('?channel_binding=require&', '?');
          return {
            type: 'postgres' as const,
            url: cleanUrl,
            ssl: { rejectUnauthorized: false },
            entities: ENTITIES,
            synchronize: false,
          };
        }
        // Fallback: local SQLite (dev without DATABASE_URL)
        return {
          type: 'better-sqlite3' as const,
          database: path.join(ROOT_DIR, 'data', 'stockadvisor.db'),
          entities: ENTITIES,
          subscribers: [SqliteDateSubscriber],
          synchronize: false,
        };
      },
    }),
    AuthModule,
    UsersModule,
    AgentRunsModule,
    ReportsModule,
    TransactionsModule,
    PortfolioModule,
    StrategiesModule,
    NotificationsModule,
    DashboardModule,
    SettingsModule,
  ],
})
export class AppModule {}
