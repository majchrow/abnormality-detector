import {Meeting} from './meeting';

export class AllMeetings {
  constructor(current: Array<Meeting>, recent: Array<Meeting>, created: Array<Meeting>) {
    this.current = current;
    this.recent = recent;
    this.created = created;
  }

  created: Array<Meeting>;
  current: Array<Meeting>;
  recent: Array<Meeting>;
}
