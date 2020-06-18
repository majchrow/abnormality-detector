import {Component, OnInit} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../services/confirmation-dialog.service';
import {NotificationService} from '../../services/notification.service';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsComponent implements OnInit {

  constructor(
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
    private notificationService: NotificationService
  ) {
  }

  config: Map<string, boolean> = new Map([
    ['notifications', true],
    ['logs', false],
    ['max participant tracking', false],
    ['date tracking', false],
    ['use X field', false],
    ['use Y field', false],
    ['use Z field', false],
    ['use T field', false]

  ]);

  ngOnInit(): void {
  }

  save() {
    this.dialogService.openConfirmDialog('Are you sure you want to save changes?')
      .afterClosed().subscribe(res => {
        if (res) {
          this.notificationService.success('Saved successfully');
        }
      }
    );
  }
}
