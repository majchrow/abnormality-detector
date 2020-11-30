export class NotificationSpec {
  constructor(type: string, name: string, event: string) {
    this.type = type;
    this.name = name;
    this.event = event;
  }

  type: string;
  name: string;
  event: string;
}
