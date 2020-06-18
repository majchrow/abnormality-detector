import {Component, OnInit} from '@angular/core';
import {Meetinginfo} from './class/meetinginfo';

@Component({
  selector: 'app-second-card',
  templateUrl: './second-card.component.html',
  styleUrls: ['./second-card.component.scss']
})
export class SecondCardComponent implements OnInit {

  constructor() {
  }

  infos: Array<Meetinginfo> = [
    new Meetinginfo(
      'biologia',
      '10/11/2011 10:15',
      '10 new warnings'
    ),
    new Meetinginfo(
      'chemia',
      '10/11/2011 15:15',
      '3 new warnings'
    ),
    new Meetinginfo(
      'informatyka',
      '10/11/2011 14:15',
      '1 new warning'
    )

  ];

  ngOnInit(): void {
  }

  move(event: MouseEvent) {
    console.log(event);
  }
}
