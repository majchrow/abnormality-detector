import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';

@Component({
  selector: 'app-meeting-card-current',
  templateUrl: './meeting-card-current.component.html',
  styleUrls: ['./meeting-card-current.component.scss']
})
export class MeetingCardCurrentComponent implements OnInit {

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
}
