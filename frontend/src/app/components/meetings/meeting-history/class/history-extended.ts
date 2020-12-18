export class HistorySpecExtended {
  constructor(type: string, startDate: Date, endDate: Date, parameter: string, reason: string, occurrence: number, conditionType: string, conditionValue: string) {
    this.startDate = startDate;
    this.endDate = endDate;
    this.parameter = parameter;
    this.reason = reason;
    this.type = type;
    this.occurrence = occurrence;
    this.conditionType = conditionType;
    this.conditionValue = conditionValue;
  }


  conditionValue: string;
  conditionType: string;
  occurrence: number;
  parameter: string;
  type: string;
  endDate: Date;
  startDate: Date;
  reason: string;
}
