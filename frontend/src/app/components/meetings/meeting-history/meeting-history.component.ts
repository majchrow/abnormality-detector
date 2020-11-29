import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {HistorySpec} from './class/history';
import {NotificationService} from '../../../services/notification.service';
import {MeetingsService} from '../../../services/meetings.service';

@Component({
  selector: 'app-meeting-history',
  templateUrl: './meeting-history.component.html',
  styleUrls: ['./meeting-history.component.scss']
})
export class MeetingHistoryComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() exitClick = new EventEmitter<any>();

  constructor(
    private notificationService: NotificationService,
    private meetingsService: MeetingsService,
  ) {
  }

  anomaliesHistory: HistorySpec[];
  displayedColumns: string[] = ['type', 'date', 'reason'];

  ngOnInit(): void {
    this.fetchHistory();
  }

  _formatDate(date: string) {
    return `${date.substr(12, 4)} ${date.substr(0, 10)}`;
  }

  fetchHistory() {
    this.meetingsService.fetchAnomalies(this.meeting, 10).subscribe(
      res => {
        this.anomaliesHistory = res.anomalies.map(
          (obj) => new HistorySpec(
            this._formatDate(obj.datetime),
            'null',
            'warning'
          )
        );
      }, err => {
        console.log(err);
      }
    );
  }

  onExitClick(): void {
    this.exitClick.emit();
  }

}
