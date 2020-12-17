import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {ConfirmationDialogService} from '../../../services/confirmation-dialog.service';

@Component({
  selector: 'app-meeting-model',
  templateUrl: './meeting-model.component.html',
  styleUrls: ['./meeting-model.component.scss']
})
export class MeetingModelComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() exitClick = new EventEmitter<any>();

  date = {begin: new Date(), end: new Date()};
  participants = 0;
  duration = 0;

  constructor(
    private dialogService: ConfirmationDialogService
  ) {
  }

  ngOnInit(): void {
  }

  onExitClick(): void {
    this.exitClick.emit();
  }

  restoreDefault() {
    this.date = {begin: new Date(), end: new Date()};
    this.participants = 0;
    this.duration = 0;

  }

  saveDate(event: any) {
    this.date = event.target.value;
  }


  formatLabel(value: number | null): string {
    if (!value) {
      return '00:00';
    }

    let hour = `${Math.floor(value / 60)}`;
    let min = `${value % 60}`;

    if (hour.length !== 2) {
      hour = '0' + hour;
    }

    if (min.length !== 2) {
      min = '0' + min;
    }
    return `${hour}:${min}`;
  }

  restore() {
    this.dialogService.openConfirmDialog('Are you sure you want to restore changes? Changes you made will not be saved.')
      .afterClosed().subscribe(res => {
        this.restoreDefault();
      }
    );
  }

  save() {
    console.log(this.date);
    console.log(this.participants);
    console.log(this.duration);
  }

}
