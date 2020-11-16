import {Meeting} from './meeting';

export class AllMeetings {
    constructor(current: Array<Meeting>, recent: Array<Meeting>, future: Array<Meeting>) {
        this.current = current;
        this.recent = recent;
        this.future = future;
    }

    future: Array<Meeting>;
    current: Array<Meeting>;
    recent: Array<Meeting>;
}
