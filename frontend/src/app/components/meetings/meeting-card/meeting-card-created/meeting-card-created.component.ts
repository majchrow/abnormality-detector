import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';

@Component({
  selector: 'app-meeting-card-created',
  templateUrl: './meeting-card-created.component.html',
  styleUrls: ['./meeting-card-created.component.scss']
})
export class MeetingCardCreatedComponent implements OnInit {

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
