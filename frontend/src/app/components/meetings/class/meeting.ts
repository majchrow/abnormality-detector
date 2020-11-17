export class Meeting {
  constructor(name: string, criteria: Array<any>) {
    this.name = name;
    this.criteria = criteria;
  }

  criteria: any = {};
  name: string;
}
