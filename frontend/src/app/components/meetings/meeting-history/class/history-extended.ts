export class HistorySpecExtended {
  constructor(type: string, startDate: Date, endDate: Date, parameter: string, reason: any, occurrence: number, conditionType: string, conditionValue: any) {
    this.startDate = startDate;
    this.endDate = endDate;
    this.parameter = parameter;
    this.reason = reason;
    this.type = type;
    this.occurrence = occurrence;
    this.conditionType = conditionType;
    this.conditionValue = conditionValue;
  }


  conditionValue: any;
  conditionType: string;
  occurrence: number;
  parameter: string;
  type: string;
  endDate: Date;
  startDate: Date;
  reason: any;
}
