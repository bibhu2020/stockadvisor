import { EventSubscriber, EntitySubscriberInterface } from 'typeorm';

/**
 * SQLite stores Python's datetime.utcnow() as bare strings like
 * "2026-06-19 14:45:00.123456" (no timezone indicator). Node's Date
 * constructor treats these as LOCAL time, baking in the dev machine's
 * UTC offset before TypeORM sets the entity property. This subscriber
 * undoes that offset so all date fields are correct UTC, matching the
 * pg-type-parser fix on the PostgreSQL path.
 */
@EventSubscriber()
export class SqliteDateSubscriber implements EntitySubscriberInterface {
  afterLoad(entity: object) {
    for (const [key, val] of Object.entries(entity)) {
      if (val instanceof Date && !isNaN(val.getTime())) {
        const offsetMs = val.getTimezoneOffset() * 60_000;
        if (offsetMs !== 0) {
          (entity as Record<string, unknown>)[key] = new Date(val.getTime() - offsetMs);
        }
      }
    }
  }
}
