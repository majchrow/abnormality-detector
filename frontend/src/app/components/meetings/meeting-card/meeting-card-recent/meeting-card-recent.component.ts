import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';

@Component({
  selector: 'app-meeting-card-recent',
  templateUrl: './meeting-card-recent.component.html',
  styleUrls: ['./meeting-card-recent.component.scss']
})
export class MeetingCardRecentComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() historyEmitter = new EventEmitter<Meeting>();
  @Output() inferenceEmitter = new EventEmitter<Meeting>();

  constructor() {
  }

  ngOnInit(): void {
  }

  onHistoryClick() {
    this.historyEmitter.emit(this.meeting);
  }

  onInferenceClick() {
    this.inferenceEmitter.emit(this.meeting);
  }

}
