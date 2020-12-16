export class HistorySpecExtended {
  constructor(type: string, startDate: string, endDate: string, parameter: string, reason: string, occurrence: number) {
    this.startDate = startDate;
    this.endDate = endDate;
    this.parameter = parameter;
    this.reason = reason;
    this.type = type;
    this.occurrence = occurrence;
  }


  occurrence: number;
  parameter: string;
  type: string;
  endDate: string;
  startDate: string;
  reason: string;
}
