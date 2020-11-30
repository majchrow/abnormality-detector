export class HistorySpec {
  constructor(date: string, reason: string, type: string) {
    this.date = date;
    this.reason = reason;
    this.type = type;
  }

  type: string;
  date: string;
  reason: string;
}
