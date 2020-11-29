import {Component, Inject, OnInit} from '@angular/core';
import {ConfirmationDialogService} from '../../../../services/confirmation-dialog.service';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

@Component({
  selector: 'app-notification-dialog',
  templateUrl: './notification-dialog.component.html',
  styleUrls: ['./notification-dialog.component.scss']
})
export class NotificationDialogComponent implements OnInit {

  constructor(
    private dialogService: ConfirmationDialogService,
    public dialogRef: MatDialogRef<NotificationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: string[]
  ) {
  }

  displayedColumns: string[] = ['type', 'name', 'event'];

  ngOnInit(): void {
  }

}
