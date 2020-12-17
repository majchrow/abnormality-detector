import {ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {HistorySpec} from './class/history';
import {NotificationService} from '../../../services/notification.service';
import {MeetingsService} from '../../../services/meetings.service';
import {HistorySpecExtended} from './class/history-extended';
import {HistoryMeeting} from './class/history-meeting';
import {FormControl, Validators} from '@angular/forms';
import {Observable} from 'rxjs';

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
    private changeDetectorRefs: ChangeDetectorRef
  ) {
  }

  anomaliesHistory: HistorySpec[];
  anomaliesHistoryView: HistorySpecExtended[];
  meetingsHistory: HistoryMeeting[];
  selectedMeeting = 'all';
  displayedColumns: string[] = ['type', 'startDate', 'endDate', 'occurrence', 'parameter', 'reason'];
  filterTypes = ['all'];
  selected = 'all';
  criteriaControl = new FormControl('', Validators.required);
  meetingControl = new FormControl('', Validators.required);

  ngOnInit(): void {
    this.fetchAllHistory();
    this.fetchHistoryMeeting();
  }

  _formatDate(date: string) {
    return `${date.substr(12, 7)} ${date.substr(0, 10)}`;
  }

  onSelectChange() {
    this.filter();
  }

  onSelectMeetingChange() {
    this.anomaliesHistoryView = null;
    const historyMeeting = this.meetingsHistory.find(el => el.start === this.selectedMeeting);
    if (this.selectedMeeting === 'all') {
      this.fetchAllHistory();
    } else {
      this.fetchHistory(historyMeeting);
    }
  }

  filter() {
    let filtered;
    if (this.selected !== 'all') {
      filtered = [...this.anomaliesHistory.filter(spec => spec.parameter === this.selected)];
    } else {
      filtered = this.anomaliesHistory;
      this.filterTypes = ['all', ...filtered.map(spec => spec.parameter).filter((value, index, self) => self.indexOf(value) === index)];
    }
    const tmpArr: HistorySpecExtended[] = [];
    let prev = null;

    for (const entry of filtered) {
      if (prev === null) {
        prev = new HistorySpecExtended(
          entry.type,
          entry.date,
          entry.date,
          entry.parameter,
          entry.reason,
          1
        );
        continue;
      }

      if (entry.parameter === prev.parameter && entry.reason === prev.reason) {
        prev.endDate = entry.date;
        prev.occurrence += 1;
      } else {
        tmpArr.push(prev);
        prev = new HistorySpecExtended(
          entry.type,
          entry.date,
          entry.date,
          entry.parameter,
          entry.reason,
          1
        );
      }
    }
    if (prev) {
      tmpArr.push(prev);
    }

    this.anomaliesHistoryView = [...tmpArr];
    this.changeDetectorRefs.detectChanges();
  }


  fetchHistory(history: HistoryMeeting) {
    this.meetingsService.fetchAnomaliesHistory(this.meeting, history).subscribe(
      res => {
        const tmp = res.anomalies;
        this.anomaliesHistory = tmp.flatMap(anomalyGroup => anomalyGroup.anomaly_reason.map(
          (anomaly, index) => new HistorySpec(
            'warning',
            this._formatDate(anomalyGroup.datetime),
            anomaly.parameter,
            anomaly.value
          )
        ));
        this.filter();
      }, err => {
        console.log(err);
      }
    );
  }

  fetchAllHistory() {
    this.meetingsService.fetchAnomalies(this.meeting).subscribe(
      res => {
        const tmp = res.anomalies;
        this.anomaliesHistory = tmp.flatMap(anomalyGroup => anomalyGroup.anomaly_reason.map(
          (anomaly, index) => new HistorySpec(
            'warning',
            this._formatDate(anomalyGroup.datetime),
            anomaly.parameter,
            anomaly.value
          )
        ));
        this.filter();
      }, err => {
        console.log(err);
      }
    );
  }

  fetchHistoryMeeting() {
    this.meetingsService.fetchMeetingHistory(this.meeting.name).subscribe(
      res => {
        this.meetingsHistory = [new HistoryMeeting('all', 'all'), ...res.calls];
      }, err => {
        console.log(err);
      }
    );
  }

  onExitClick(): void {
    this.exitClick.emit();
  }

  generateReport() {
    let sub: Observable<any>;
    if (this.selectedMeeting === 'all') {
      sub = this.meetingsService.getAllReports(this.meeting);
    } else {
      const historyMeeting = this.meetingsHistory.find(el => el.start === this.selectedMeeting);

      sub = this.meetingsService.getReports(this.meeting, historyMeeting);
    }
    sub.subscribe(
      next => {
        const fileURL = URL.createObjectURL(next);
        window.open(fileURL, '_blank');
      },
      err => {
        console.log(err);
      }
    );
  }

}
