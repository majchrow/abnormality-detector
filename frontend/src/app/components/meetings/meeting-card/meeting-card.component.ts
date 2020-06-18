import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';

@Component({
  selector: 'app-meeting-card',
  templateUrl: './meeting-card.component.html',
  styleUrls: ['./meeting-card.component.scss']
})
export class MeetingCardComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() deleted = new EventEmitter<Meeting>();

  constructor() {
  }

  ngOnInit(): void {
  }

  edit(event: MouseEvent) {
    console.log('edit');
  }

  delete(event: MouseEvent) {
    this.deleted.emit(this.meeting);
  }

}
