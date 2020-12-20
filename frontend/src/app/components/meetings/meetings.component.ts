import {Component, OnInit} from '@angular/core';
import {Meeting} from './class/meeting';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../services/confirmation-dialog.service';
import {NotificationService} from '../../services/notification.service';
import {MeetingsService} from '../../services/meetings.service';
import {AllMeetings} from './class/all-meetings';
import {NewMeetingDialogComponent} from './new-meeting-dialog/new-meeting-dialog.component';

@Component({
  selector: 'app-meetings',
  templateUrl: './meetings.component.html',
  styleUrls: ['./meetings.component.scss']
})
export class MeetingsComponent implements OnInit {

  constructor(
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
    private notificationService: NotificationService,
    private meetingsService: MeetingsService
  ) {
  }

  selected: string;
  val: string;
  id: string;
  settingMeeting: Meeting;
  historyMeeting: Meeting;
  modelMeeting: Meeting;
  inferenceMeeting: Meeting;
  allMeetings: AllMeetings;
  selectedMeetings: AllMeetings;
  viewMeetings: AllMeetings;
  meetingType = 'current';

  ngOnInit(): void {
    this.initAllMeetings();
  }

  initAllMeetings() {
    this.resetMeetings();
    this.selected = 'None';
    this.subscribeRest();
  }

  onSuccessCriteria() {
    this.selected = '';
    this.meetingType = 'created';
    this.resetMeetings();
    this.subscribeRest();
  }

  onSettingClick(meeting: Meeting) {
    this.settingMeeting = meeting;
    this.selected = 'setting';
  }

  onHistoryClick(meeting: Meeting) {
    this.historyMeeting = meeting;
    this.selected = 'history';
  }

  onModelClick(meeting: Meeting) {
    this.modelMeeting = meeting;
    this.selected = 'model';
  }

  onInferenceClick(meeting: Meeting) {
    this.inferenceMeeting = meeting;
    this.selected = 'inference';
  }

  resetMeetings() {
    this.allMeetings = null;
    this.selectedMeetings = null;
    this.viewMeetings = null;
  }


  subscribeRest() {
    this.meetingsService.fetchMeetings().subscribe(
      next => {
        this.allMeetings = next;
        this.filterMeetings();
      },
      error => {
        this.notificationService.warn(error.message);
      }
    );
  }

  filterNames(prefix: string) {
    this.viewMeetings = new AllMeetings([...this.selectedMeetings.current], [...this.selectedMeetings.recent], [...this.selectedMeetings.created]);
    this.viewMeetings.current = this.selectedMeetings.current.filter(meeting => meeting.name.toLowerCase().includes(prefix.toLowerCase()));
    this.viewMeetings.recent = this.selectedMeetings.recent.filter(meeting => meeting.name.toLowerCase().includes(prefix.toLowerCase()));
    this.viewMeetings.created = this.selectedMeetings.created.filter(meeting => meeting.name.toLowerCase().includes(prefix.toLowerCase()));
  }

  filterIds(prefix: string) {
    this.viewMeetings = new AllMeetings([...this.selectedMeetings.current], [...this.selectedMeetings.recent], [...this.selectedMeetings.created]);
    this.viewMeetings.current = this.selectedMeetings.current.filter(meeting => meeting.meeting_number.toString().startsWith(prefix));
    this.viewMeetings.recent = this.selectedMeetings.recent.filter(meeting => meeting.meeting_number.toString().startsWith(prefix));
    this.viewMeetings.created = this.selectedMeetings.created.filter(meeting => meeting.meeting_number.toString().startsWith(prefix));
  }

  changeMeetingType(selected: string) {
    this.meetingType = selected;
    this.resetMeetings();
    this.subscribeRest();
  }

  filterMeetings() {
    switch (this.meetingType) {
      case 'created': {
        this.selectedMeetings = new AllMeetings([], [], [...this.allMeetings.created]);
        break;
      }
      case 'current': {
        this.selectedMeetings = new AllMeetings([...this.allMeetings.current], [], []);
        break;
      }
      case 'recent': {
        this.selectedMeetings = new AllMeetings([], [...this.allMeetings.recent], []);
        break;
      }
      default: {
        this.selectedMeetings = new AllMeetings([...this.allMeetings.current], [...this.allMeetings.recent], [...this.allMeetings.created]);
      }
    }
    this.filterNames('');
    this.filterIds('');
  }

  onDeleteClick(meeting: Meeting) {
    this.dialogService.openConfirmDialog('Are you sure you want to delete this room?')
      .afterClosed().subscribe(res => {
      if (res) {
        this.meetingsService.deleteMeeting(meeting).subscribe(
          () => {
            this.notificationService.success('Room successfully deleted from observed');
            this.resetMeetings();
            this.subscribeRest();
          }, () => {
            this.notificationService.warn('Failed to delete room from observed');
          }
        );
      }
    });
  }

  newMeetingDialog(): void {
    const dialogRef = this.dialog.open(NewMeetingDialogComponent, {
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(() => {
      this.resetMeetings();
      this.subscribeRest();
    });
  }

}
