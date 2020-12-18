export class HistorySpec {
  constructor(type: string, date: Date, parameter: string, reason: string, conditionType: string, conditionValue: string) {
    this.date = date;
    this.parameter = parameter;
    this.reason = reason;
    this.type = type;
    this.conditionType = conditionType;
    this.conditionValue = conditionValue;

  }

  conditionValue: string;
  conditionType: string;
  parameter: string;
  type: string;
  date: Date;
  reason: string;
}
