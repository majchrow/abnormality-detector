export class HistorySpec {
  constructor(type: string, date: Date, parameter: string, reason: any, conditionType: string, conditionValue: any) {
    this.date = date;
    this.parameter = parameter;
    this.reason = reason;
    this.type = type;
    this.conditionType = conditionType;
    this.conditionValue = conditionValue;

  }

  conditionValue: any;
  conditionType: string;
  parameter: string;
  type: string;
  date: Date;
  reason: any;
}
