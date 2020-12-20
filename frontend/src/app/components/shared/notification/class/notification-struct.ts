export class NotificationSpec {
  constructor(type: string, name: string, event: string, date: Date, highlight: boolean) {
    this.type = type;
    this.name = name;
    this.event = event;
    this.date = date;
    this.highlight = highlight;
  }

  date: Date;
  type: string;
  name: string;
  event: string;
  highlight: boolean;
}
