import {Component, OnInit} from '@angular/core';

@Component({
  selector: 'app-third-card',
  templateUrl: './third-card.component.html',
  styleUrls: ['./third-card.component.scss']
})
export class ThirdCardComponent implements OnInit {

  constructor() {
  }

  infos: Array<string> = [
    'Active meetings: 4',
    'Last error: 4/1/2021 10:15',
    'Abnormalities found today: 10'
  ];

  ngOnInit(): void {
  }

}
