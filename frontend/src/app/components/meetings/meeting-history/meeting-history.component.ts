import {ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../class/meeting';
import {HistorySpec} from './class/history';
import {NotificationService} from '../../../services/notification.service';
import {MeetingsService} from '../../../services/meetings.service';
import {HistorySpecExtended} from './class/history-extended';
import {HistoryMeeting} from './class/history-meeting';
import {Observable} from 'rxjs';
import {saveAs} from 'file-saver';

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


  options = {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };

  options2 = {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };

  anomaliesHistory: HistorySpec[];
  anomaliesHistoryTmp: HistorySpec[];
  anomaliesHistoryView: HistorySpecExtended[];
  meetingsHistory: HistoryMeeting[];
  displayedColumns: string[] = ['type', 'startDate', 'endDate', 'occurrence', 'parameter', 'conditionType', 'reason', 'conditionValue'];
  filterTypes = ['all'];
  filterModels = ['all', 'ml model', 'admin model'];
  selected = 'all';
  selectedModel = 'all';
  selectedMeeting = 'all';

  ngOnInit(): void {
    this.fetchAllHistory();
    this.fetchHistoryMeeting();
  }

  // _formatDate(date: string) {
  //   return `${date.substr(12, 7)} ${date.substr(0, 10)}`;
  // }

  translateDay(key: string) {
    return {
      1: 'Mon',
      2: 'Tue',
      3: 'Wed',
      4: 'Thu',
      5: 'Fri',
      6: 'Sat',
      7: 'Sun'
    }[key];
  }

  onSelectChange() {
    this.filter();
  }

  onSelectMeetingChange() {
    this.anomaliesHistoryView = null;
    const historyMeeting = this.meetingsHistory.find(el => el.start.toISOString() === this.selectedMeeting);
    if (this.selectedMeeting === 'all') {
      this.fetchAllHistory();
    } else {
      this.fetchHistory(historyMeeting);
    }
    this.filter();
  }

  onSelectModelChange() {
    this.filter();
  }

  arraysEqual(a1, a2) {
    return JSON.stringify(a1) === JSON.stringify(a2);
  }

  filterModel() {
    switch (this.selectedModel) {
      case 'ml model': {
        this.anomaliesHistoryTmp = [...this.anomaliesHistory.filter(row => row.parameter === 'ml_model')];
        break;
      }
      case 'admin model': {
        this.anomaliesHistoryTmp = [...this.anomaliesHistory.filter(row => row.parameter !== 'ml_model')];
        break;
      }
      default: {
        this.anomaliesHistoryTmp = [...this.anomaliesHistory];
        break;
      }
    }
  }

  filterCriteria() {
    if (this.selected !== 'all') {
      this.anomaliesHistoryTmp = [...this.anomaliesHistoryTmp.filter(spec => spec.parameter === this.selected)];
    }
  }

  filterPhaseThree() {
    const filtered = this.anomaliesHistoryTmp;
    const tmpArr: HistorySpecExtended[] = [];
    let prev = null;

    for (const entry of filtered) {
      if (prev === null) {
        prev = new HistorySpecExtended(
          entry.type,
          entry.date,
          entry.date,
          entry.parameter,
          entry.parameter === 'day' ? this.translateDay(entry.reason) : entry.reason,
          1,
          entry.conditionType,
          entry.parameter === 'day' ? entry.conditionValue.map(day => this.translateDay(day)) : entry.conditionValue
        );
        continue;
      }

      // tslint:disable-next-line:max-line-length
      if (entry.parameter === prev.parameter && entry.conditionType === prev.conditionType &&
        // tslint:disable-next-line:max-line-length
        (entry.parameter === 'day' && this.translateDay(entry.reason) === prev.reason && this.arraysEqual(entry.conditionValue.map(day => this.translateDay(day)), prev.conditionValue) ||
          (entry.reason === prev.reason && this.arraysEqual(entry.conditionValue, prev.conditionValue))
        )) {
        prev.endDate = entry.date;
        prev.occurrence += 1;
      } else {
        tmpArr.push(prev);
        prev = new HistorySpecExtended(
          entry.type,
          entry.date,
          entry.date,
          entry.parameter,
          entry.parameter === 'day' ? this.translateDay(entry.reason) : entry.parameter === 'prob' ? entry.reason : entry.reason,
          1,
          entry.conditionType,
          entry.parameter === 'day' ? entry.conditionValue.map(day => this.translateDay(day)) : entry.conditionValue
        );
      }
    }
    if (prev) {
      tmpArr.push(prev);
    }

    this.anomaliesHistoryView = [...tmpArr.reverse()];
    this.anomaliesHistoryView = this.anomaliesHistoryView.slice(0, 100);
    this.changeDetectorRefs.detectChanges();
  }

  filter() {
    this.filterModel();
    this.filterCriteria();
    this.filterPhaseThree();


  }


  fetchHistory(history: HistoryMeeting) {
    this.meetingsService.fetchAnomaliesHistory(this.meeting, history).subscribe(
      res => {
        const tmp = res.anomalies;
        this.anomaliesHistory = tmp.flatMap(anomalyGroup => anomalyGroup.anomaly_reason.map(
          (anomaly, index) => new HistorySpec(
            anomaly.parameter === 'current_participants' ? 'max_participants' : anomaly.parameter,
            new Date(Date.parse(anomalyGroup.datetime)),
            anomaly.parameter === 'current_participants' ? 'max_participants' : anomaly.parameter,
            anomaly.parameter === 'ml_model' ? (anomaly.value * 100).toFixed(2) + '%' :
              anomaly.parameter === 'datetime' ? anomaly.value.substr(0, 8) : anomaly.value,
            anomaly.condition_type,
            anomaly.parameter === 'ml_model' ? (anomaly.condition_value * 100).toFixed(2) + '%' : anomaly.condition_value
          )
        ));
        // tslint:disable-next-line:max-line-length
        this.filterTypes = ['all', ...this.anomaliesHistory.map(spec => spec.parameter).filter((value, index, self) => self.indexOf(value) === index).filter(el => el !== 'ml_model')];
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
            anomaly.parameter === 'current_participants' ? 'max_participants' : anomaly.parameter,
            new Date(Date.parse(anomalyGroup.datetime)),
            anomaly.parameter === 'current_participants' ? 'max_participants' : anomaly.parameter,
            anomaly.parameter === 'ml_model' ? (anomaly.value * 100).toFixed(2) + '%' :
              anomaly.parameter === 'datetime' ? anomaly.value.substr(0, 8) : anomaly.value,
            anomaly.condition_type,
            anomaly.parameter === 'ml_model' ? (anomaly.condition_value * 100).toFixed(2) + '%' : anomaly.condition_value
          )
        ));
        // tslint:disable-next-line:max-line-length
        this.filterTypes = ['all', ...this.anomaliesHistory.map(spec => spec.parameter).filter((value, index, self) => self.indexOf(value) === index).filter(el => el !== 'ml_model')];
        this.filter();
      }, err => {
        console.log(err);
      }
    );
  }

  fetchHistoryMeeting() {
    this.meetingsService.fetchMeetingHistory(this.meeting.name).subscribe(
      res => {
        this.meetingsHistory = res.calls.map(el => new HistoryMeeting(new Date(Date.parse(el.start)), new Date(Date.parse(el.end))));
      }, err => {
        console.log(err);
      }
    );
  }

  onExitClick(): void {
    this.exitClick.emit();
  }

  downloadZip() {
    let sub: Observable<any>;
    const historyMeeting = this.meetingsHistory.find(el => el.start.toISOString() === this.selectedMeeting);
    if (this.selectedMeeting === 'all') {
      console.log('not supported');
    } else {
      sub = this.meetingsService.downloadZip(this.meeting, historyMeeting);
    }
    sub.subscribe(
      next => {
        let filename = `${this.meeting.name}_${historyMeeting.start.toLocaleString('en-GB', this.options2)}.zip`;
        filename = filename.split(' ').join('_');
        filename = filename.split(',').join('_');
        filename = filename.split(':').join('_');
        filename = filename.split('-').join('_');
        filename = filename.split('__').join('_');
        saveAs(next, filename);
      },
      err => {
        console.log(err);
      }
    );
  }

  generateReport() {
    let sub: Observable<any>;
    if (this.selectedMeeting === 'all') {
      sub = this.meetingsService.getAllReports(this.meeting);
    } else {
      const historyMeeting = this.meetingsHistory.find(el => el.start.toISOString() === this.selectedMeeting);

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
