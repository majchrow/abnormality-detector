export class Meeting {
  // tslint:disable-next-line:variable-name
  constructor(name: string, meeting_number: number, criteria: Array<any>) {
    this.name = name;
    this.criteria = criteria;
    this.meeting_number = meeting_number;
  }

  // tslint:disable-next-line:variable-name
  meeting_number: number;
  criteria: Array<any>;
  name: string;
}
