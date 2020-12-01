export class HistorySpec {
  constructor(type: string, date: string, parameter: string, reason: string) {
    this.date = date;
    this.parameter = parameter;
    this.reason = reason;
    this.type = type;
  }

  parameter: string;
  type: string;
  date: string;
  reason: string;
}
