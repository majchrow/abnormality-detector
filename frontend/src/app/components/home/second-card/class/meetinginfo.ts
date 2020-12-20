export class Meetinginfo {
  constructor(meeting: string, date: Date, info: string, status: string) {
    this.status = status;
    this.meeting = meeting;
    this.date = date;
    this.info = info;
  }

  status: string;
  meeting: string;
  date: Date;
  info: string;


}
