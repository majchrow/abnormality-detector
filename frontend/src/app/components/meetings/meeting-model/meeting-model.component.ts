import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {FormGroup, FormControl} from '@angular/forms';

@Component({
  selector: 'app-meeting-model',
  templateUrl: './meeting-model.component.html',
  styleUrls: ['./meeting-model.component.scss']
})
export class MeetingModelComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() exitClick = new EventEmitter<any>();

  range = new FormGroup({
    start: new FormControl(),
    end: new FormControl()
  });

  constructor() {
  }

  ngOnInit(): void {
  }

  onExitClick(): void {
    this.exitClick.emit();
  }

}
