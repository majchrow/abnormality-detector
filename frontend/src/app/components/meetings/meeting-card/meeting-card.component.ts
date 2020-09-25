import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';

@Component({
  selector: 'app-meeting-card',
  templateUrl: './meeting-card.component.html',
  styleUrls: ['./meeting-card.component.scss']
})
export class MeetingCardComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() deleteEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();

  constructor() {
  }

  ngOnInit(): void {
  }

  settings(event: MouseEvent) {
    this.settingEmitter.emit(this.meeting);
  }

  edit(event: MouseEvent) {
    console.log('edit');
  }

  delete(event: MouseEvent) {
    this.deleteEmitter.emit(this.meeting);
  }

}
